"""Profile snapshots, readiness estimates, and fact-protection helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import CareerMemory, InterviewSession, Profile, Resume, Roadmap, User
from app.services.catalog import flatten_skills


def ensure_profile(db: Session, user: User) -> Profile:
    if user.profile:
        return user.profile
    profile = Profile(
        user_id=user.id,
        skills={
            "craft": [],
            "domain": [],
            "programming": [],
            "frameworks": [],
            "tools": [],
            "platforms": [],
            "technical": [],
            "soft": [],
            "certifications": [],
        },
        career_goals={
            "desired_career": "",
            "desired_role": "",
            "desired_industry": "",
            "experience_level": "entry",
            "short_term_goal": "",
            "long_term_goal": "",
        },
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def profile_is_complete(profile: Profile) -> bool:
    skills = flatten_skills(profile.skills or {})
    goals = profile.career_goals or {}
    return bool(
        profile.user.full_name
        and (profile.education or profile.experience or profile.projects)
        and skills
        and (goals.get("desired_role") or goals.get("desired_career"))
    )


def profile_to_text(user: User, profile: Profile) -> str:
    skills = flatten_skills(profile.skills or {})
    goals = profile.career_goals or {}
    parts = [
        f"Name: {user.full_name}",
        f"Status: {profile.professional_status}",
        f"Location: {profile.city}, {profile.country}".strip(", "),
        f"Headline: {profile.headline}",
        f"Summary: {profile.summary}",
        f"Education: {profile.education}",
        f"Experience: {profile.experience}",
        f"Skills: {', '.join(skills)}",
        f"Projects: {profile.projects}",
        f"Desired role: {goals.get('desired_role') or goals.get('desired_career')}",
        f"Industry: {goals.get('desired_industry')}",
        f"Level: {goals.get('experience_level')}",
        f"Short-term: {goals.get('short_term_goal')}",
        f"Long-term: {goals.get('long_term_goal')}",
    ]
    return "\n".join(parts)


def allowed_facts(user: User, profile: Profile) -> dict[str, list[str]]:
    companies = [str(e.get("company", "")) for e in (profile.experience or []) if e.get("company")]
    titles = [str(e.get("title", "")) for e in (profile.experience or []) if e.get("title")]
    degrees = [str(e.get("degree", "")) for e in (profile.education or []) if e.get("degree")]
    schools = [str(e.get("institution", "")) for e in (profile.education or []) if e.get("institution")]
    projects = [str(p.get("name", "")) for p in (profile.projects or []) if p.get("name")]
    skills = flatten_skills(profile.skills or {})
    return {
        "name": [user.full_name],
        "companies": companies,
        "titles": titles,
        "degrees": degrees,
        "schools": schools,
        "projects": projects,
        "skills": skills,
    }


def memory_text(db: Session, user_id: int) -> str:
    rows = (
        db.query(CareerMemory)
        .filter_by(user_id=user_id, enabled=True)
        .all()
    )
    if not rows:
        return ""
    return "\n".join(f"- [{m.category}] {m.key}: {m.value}" for m in rows)


def maybe_store_memory(db: Session, user: User, key: str, value: str, category: str = "preference") -> None:
    from app.services.billing import limits_for

    if not limits_for(user).get("career_memory"):
        return
    existing = db.query(CareerMemory).filter_by(user_id=user.id, key=key).first()
    if existing:
        existing.value = value
        existing.category = category
    else:
        db.add(CareerMemory(user_id=user.id, key=key, value=value, category=category))
    db.commit()


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in ("", "nothing", "n/a", "na", "-", "none")
    if isinstance(value, list):
        return any(_nonempty(v) for v in value)
    if isinstance(value, dict):
        return any(_nonempty(v) for v in value.values())
    return True


def _resume_content_score(content: dict[str, Any]) -> float:
    """0 until the document has real sections — a name and email are not 'healthy'."""
    score = 0.0
    if _nonempty((content.get("summary") or "").strip()):
        score += 16
    if _nonempty(content.get("experience")):
        score += 28
    if _nonempty(content.get("education")):
        score += 16
    if _nonempty(content.get("skills")):
        score += 20
    if _nonempty(content.get("projects")):
        score += 20
    return min(100.0, score)


def _usable_ats(last_ats: dict[str, Any] | None) -> float | None:
    if not last_ats:
        return None
    if not last_ats.get("had_jd"):
        return None
    ats = last_ats.get("ats_readiness")
    if isinstance(ats, (int, float)) and ats >= 0:
        return float(ats)
    return None


def recompute_scores(db: Session, user: User) -> Profile:
    """The three dashboard gauges start at 0 and rise only from app activity."""
    profile = ensure_profile(db, user)

    resumes = db.query(Resume).filter_by(user_id=user.id, is_active=True).all()
    resume_health = 0.0
    if resumes:
        scores = []
        for r in resumes:
            ats = _usable_ats(r.last_ats if isinstance(r.last_ats, dict) else None)
            if ats is not None:
                scores.append(ats)
            else:
                scores.append(_resume_content_score(r.content or {}))
        resume_health = sum(scores) / len(scores)

    sessions = (
        db.query(InterviewSession)
        .filter_by(user_id=user.id, status="completed")
        .all()
    )
    interview = 0.0
    if sessions:
        interview = sum(s.overall_score or 0 for s in sessions) / len(sessions)

    roadmap = (
        db.query(Roadmap)
        .filter_by(user_id=user.id)
        .order_by(Roadmap.updated_at.desc())
        .first()
    )
    gap_pts = 0.0
    extra = 0.0
    if roadmap:
        from app.agents.career import readiness_from_gaps

        if roadmap.skill_gap:
            gap_pts = readiness_from_gaps(roadmap.skill_gap) * 0.4
        tasks = [t for m in (roadmap.milestones or []) for t in m.get("tasks", [])]
        if tasks:
            extra = 12 * (sum(1 for t in tasks if t.get("completed")) / len(tasks))

    readiness = gap_pts + resume_health * 0.3 + interview * 0.3 + extra
    profile.readiness_score = round(min(98, readiness), 1)
    profile.resume_health = round(resume_health, 1)
    profile.interview_performance = round(interview, 1)
    db.commit()
    db.refresh(profile)
    return profile


def next_action(profile: Profile, db: Session, user_id: int) -> str:
    if not profile_is_complete(profile):
        return "Finish your career profile so every feature can use the same facts."
    if not db.query(Resume).filter_by(user_id=user_id, is_active=True).count():
        return "Create or upload a master resume from your profile."
    if (profile.resume_health or 0) < 75:
        return "Run ATS analysis on your resume and close the flagged gaps."
    if not db.query(InterviewSession).filter_by(user_id=user_id).count():
        return "Practice a mock interview for your target role."
    if (profile.interview_performance or 0) < 70:
        return "Practice a mock interview for your target role — scores suggest structure needs work."
    roadmap = db.query(Roadmap).filter_by(user_id=user_id).order_by(Roadmap.updated_at.desc()).first()
    if roadmap:
        for m in roadmap.milestones or []:
            for t in m.get("tasks", []):
                if not t.get("completed"):
                    return f"Continue your roadmap: {t.get('title') or t.get('skill') or 'next task'}."
    return "Compare two career paths or tailor a resume to a job description."


def dashboard_payload(db: Session, user: User) -> dict[str, Any]:
    profile = recompute_scores(db, user)
    goals = profile.career_goals or {}
    roadmap = (
        db.query(Roadmap)
        .filter_by(user_id=user.id)
        .order_by(Roadmap.updated_at.desc())
        .first()
    )
    top_gaps = []
    week = None
    if roadmap:
        top_gaps = [
            g.get("skill")
            for g in (roadmap.skill_gap or [])
            if g.get("gap") in ("high", "medium")
        ][:3]
        tasks = [t for m in (roadmap.milestones or []) for t in m.get("tasks", [])]
        done = sum(1 for t in tasks if t.get("completed"))
        week = f"{done} of {len(tasks)} tasks" if tasks else None

    interviews = db.query(InterviewSession).filter_by(user_id=user.id).count()
    resumes = db.query(Resume).filter_by(user_id=user.id, is_active=True).count()
    from app.services.reminders import list_reminders

    due = list_reminders(db, user)[:3]
    return {
        "career_goal": goals.get("desired_role") or goals.get("desired_career") or "Not set",
        "readiness": profile.readiness_score,
        "resume_health": profile.resume_health,
        "interview_performance": profile.interview_performance,
        "top_skill_gaps": top_gaps,
        "roadmap_progress": week,
        "next_action": next_action(profile, db, user.id),
        "counts": {
            "resumes": resumes,
            "interviews": interviews,
            "roadmaps": db.query(Roadmap).filter_by(user_id=user.id).count(),
        },
        "due_reminders": due[:3],
        "profile_complete": profile_is_complete(profile),
        "disclaimer": "Readiness is an AI-generated estimate for personal tracking, not a hiring guarantee.",
    }
