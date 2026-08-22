from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbDep
from app.models import CareerMemory, Conversation, InterviewSession, Profile, ProfileImport, Reminder, Resume, Roadmap, UsageRecord, User
from app.schemas import ProfileIn, ProfileOut
from app.services.checkout import cancel_stripe_billing
from app.services.profile import dashboard_payload, ensure_profile, recompute_scores

router = APIRouter(prefix="/api", tags=["profile"])


def _out(user: User, profile: Profile) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        country=profile.country,
        city=profile.city,
        professional_status=profile.professional_status,
        headline=profile.headline,
        summary=profile.summary,
        education=profile.education or [],
        experience=profile.experience or [],
        skills=profile.skills or {},
        projects=profile.projects or [],
        career_goals=profile.career_goals or {},
        linkedin_url=getattr(profile, "linkedin_url", "") or "",
        github_username=getattr(profile, "github_username", "") or "",
        readiness_score=profile.readiness_score,
        resume_health=profile.resume_health,
        interview_performance=profile.interview_performance,
        plan=user.plan,
        updated_at=profile.updated_at,
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: CurrentUser, db: DbDep):
    profile = ensure_profile(db, user)
    return _out(user, profile)


@router.put("/profile", response_model=ProfileOut)
def update_profile(payload: ProfileIn, user: CurrentUser, db: DbDep):
    profile = ensure_profile(db, user)
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        elif isinstance(value, list):
            value = [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
        setattr(profile, key, value)
    db.commit()
    profile = recompute_scores(db, user)
    return _out(user, profile)


@router.get("/dashboard")
def dashboard(user: CurrentUser, db: DbDep):
    return dashboard_payload(db, user)


@router.get("/account/export")
def export_account(user: CurrentUser, db: DbDep):
    profile = ensure_profile(db, user)
    return {
        "user": {"email": user.email, "full_name": user.full_name, "plan": user.plan},
        "profile": {
            "country": profile.country,
            "city": profile.city,
            "professional_status": profile.professional_status,
            "headline": profile.headline,
            "summary": profile.summary,
            "education": profile.education,
            "experience": profile.experience,
            "skills": profile.skills,
            "projects": profile.projects,
            "career_goals": profile.career_goals,
            "linkedin_url": getattr(profile, "linkedin_url", ""),
            "github_username": getattr(profile, "github_username", ""),
        },
        "resumes": [
            {"id": r.id, "title": r.title, "content": r.content} for r in user.resumes
        ],
        "memories": [
            {"category": m.category, "key": m.key, "value": m.value}
            for m in db.query(CareerMemory).filter_by(user_id=user.id).all()
        ],
        "interviews": [
            {"id": s.id, "target_role": s.target_role, "overall_score": s.overall_score, "report": s.report}
            for s in user.interviews
        ],
    }


@router.delete("/account")
def delete_account(user: CurrentUser, db: DbDep):
    cancel_stripe_billing(user, required=False, delete_customer=True)
    uid = user.id
    db.query(CareerMemory).filter_by(user_id=uid).delete()
    db.query(Conversation).filter_by(user_id=uid).delete()
    db.query(InterviewSession).filter_by(user_id=uid).delete()
    db.query(Resume).filter_by(user_id=uid).delete()
    db.query(Roadmap).filter_by(user_id=uid).delete()
    db.query(UsageRecord).filter_by(user_id=uid).delete()
    db.query(Reminder).filter_by(user_id=uid).delete()
    db.query(ProfileImport).filter_by(user_id=uid).delete()
    db.query(Profile).filter_by(user_id=uid).delete()
    db.delete(user)
    db.commit()
    return {"ok": True}
