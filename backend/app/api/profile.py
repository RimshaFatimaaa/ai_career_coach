from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbDep
from app.models import (
    CareerMemory,
    Conversation,
    InterviewSession,
    Profile,
    ProfileImport,
    Reminder,
    Resume,
    Roadmap,
    UsageRecord,
    User,
    utcnow,
)
from app.schemas import AccountDeleteIn, ProfileIn, ProfileOut
from app.services.auth import verify_password
from app.services.checkout import cancel_stripe_billing
from app.services.profile import dashboard_payload, ensure_profile, recompute_scores
from app.services.storage import delete_path

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
    # full_name lives on the user but is required for profile completeness, so
    # it has to be editable from the profile screen.
    full_name = str(data.pop("full_name", "") or "").strip()
    if full_name:
        user.full_name = full_name[:255]
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
        "exported_at": utcnow(),
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "plan": user.plan,
            "role": user.role,
            "created_at": user.created_at,
            "terms_accepted_at": user.terms_accepted_at,
        },
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
            {
                "id": r.id,
                "title": r.title,
                "version_type": r.version_type,
                "template": r.template,
                "source": r.source,
                "target_role": r.target_role,
                "content": r.content,
                "change_log": r.change_log,
                "last_ats": r.last_ats,
                "is_active": r.is_active,
                "created_at": r.created_at,
            }
            for r in user.resumes
        ],
        "memories": [
            {"category": m.category, "key": m.key, "value": m.value, "enabled": m.enabled}
            for m in db.query(CareerMemory).filter_by(user_id=user.id).all()
        ],
        "interviews": [
            {
                "id": s.id,
                "target_role": s.target_role,
                "interview_type": s.interview_type,
                "status": s.status,
                "overall_score": s.overall_score,
                "questions": s.questions,
                "report": s.report,
                "created_at": s.created_at,
            }
            for s in user.interviews
        ],
        "roadmaps": [
            {
                "id": r.id,
                "target_role": r.target_role,
                "duration_months": r.duration_months,
                "milestones": r.milestones,
                "skill_gap": r.skill_gap,
                "is_saved": r.is_saved,
                "created_at": r.created_at,
            }
            for r in db.query(Roadmap).filter_by(user_id=user.id).all()
        ],
        "conversations": [
            {"id": c.id, "title": c.title, "messages": c.messages, "created_at": c.created_at}
            for c in db.query(Conversation).filter_by(user_id=user.id).all()
        ],
        "reminders": [
            {
                "id": r.id,
                "title": r.title,
                "body": r.body,
                "due_at": r.due_at,
                "source": r.source,
                "done": r.done,
            }
            for r in db.query(Reminder).filter_by(user_id=user.id).all()
        ],
        "imports": [
            {"id": i.id, "source": i.source, "handle": i.handle, "analysis": i.analysis, "applied": i.applied}
            for i in db.query(ProfileImport).filter_by(user_id=user.id).all()
        ],
        "usage": [
            {"feature": u.feature, "period": u.period, "count": u.count}
            for u in db.query(UsageRecord).filter_by(user_id=user.id).all()
        ],
    }


@router.delete("/account")
def delete_account(payload: AccountDeleteIn, user: CurrentUser, db: DbDep):
    """Irreversible, so it needs the password — a stolen token is not enough."""
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(403, "Enter your account password to delete your account.")
    cancel_stripe_billing(user, required=False, delete_customer=True)
    uid = user.id
    for resume in db.query(Resume).filter_by(user_id=uid).all():
        if resume.file_path:
            delete_path(resume.file_path)
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
