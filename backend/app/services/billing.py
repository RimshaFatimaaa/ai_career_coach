"""Subscription limits and usage tracking — PRD §13."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import UsageRecord, User

PLAN_LIMITS = {
    "free": {
        "active_resumes": 1,
        "resume_analyses": 3,
        "resume_generations": 2,
        "resume_uploads": 3,
        "tailorings": 2,
        "mock_interviews": 1,
        "interview_questions": 15,
        "cover_letters": 1,
        "career_chats": 40,
        "profile_imports": 5,
        "skill_gap_analyses": 15,
        "roadmaps": 5,
        "docx_export": False,
        "career_memory": False,
        "advanced_analysis": False,
        "voice_interviews": False,
        "templates": ["ats_classic", "graduate"],
    },
    "pro": {
        "active_resumes": 8,
        "resume_analyses": 20,
        "resume_generations": 15,
        "resume_uploads": 25,
        "tailorings": 15,
        "mock_interviews": 10,
        "interview_questions": 150,
        "cover_letters": 20,
        "career_chats": 400,
        "profile_imports": 40,
        "skill_gap_analyses": 120,
        "roadmaps": 40,
        "docx_export": True,
        "career_memory": True,
        "advanced_analysis": True,
        "voice_interviews": False,
        "templates": ["ats_classic", "modern_ats", "technical", "graduate", "executive"],
    },
    "premium": {
        "active_resumes": 30,
        "resume_analyses": 80,
        "resume_generations": 60,
        "resume_uploads": 100,
        "tailorings": 60,
        "mock_interviews": 40,
        "interview_questions": 600,
        "cover_letters": 80,
        "career_chats": 2000,
        "profile_imports": 200,
        "skill_gap_analyses": 600,
        "roadmaps": 200,
        "docx_export": True,
        "career_memory": True,
        "advanced_analysis": True,
        "voice_interviews": True,
        "templates": [
            "ats_classic",
            "modern_ats",
            "technical",
            "graduate",
            "executive",
            "compact",
            "portfolio",
            "two_tone",
        ],
    },
}

METERED_FEATURES = [
    "resume_analyses",
    "resume_generations",
    "resume_uploads",
    "tailorings",
    "mock_interviews",
    "interview_questions",
    "cover_letters",
    "career_chats",
    "profile_imports",
    "skill_gap_analyses",
    "roadmaps",
]

FEATURE_KEYS = {key: key for key in METERED_FEATURES}


def period_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def limits_for(user: User) -> dict:
    plan = (getattr(user, "plan", None) or "free").strip().lower()
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def assert_template_allowed(user: User, template: str) -> None:
    """Templates are re-checked on every render, not just at creation.

    Otherwise a user generates on Premium, downgrades, and keeps exporting the
    paid designs forever.
    """
    allowed = limits_for(user)["templates"]
    if template and template not in allowed:
        plan = (getattr(user, "plan", None) or "free").strip().lower()
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"The {template.replace('_', ' ')} template is not included in the {plan} plan. "
            f"Switch this resume to {allowed[0].replace('_', ' ')} or upgrade to keep the design.",
        )


def get_usage(db: Session, user_id: int, feature: str) -> int:
    total = (
        db.query(func.coalesce(func.sum(UsageRecord.count), 0))
        .filter_by(user_id=user_id, feature=feature, period=period_key())
        .scalar()
    )
    return int(total or 0)


def assert_within_limit(db: Session, user: User, feature: str, amount: int = 1) -> None:
    limits = limits_for(user)
    cap = limits.get(feature)
    if cap is False:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"{feature} requires a paid plan")
    if isinstance(cap, int):
        used = get_usage(db, user.id, feature)
        if used + amount > cap:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"{user.plan.title()} plan limit reached for {feature.replace('_', ' ')} ({used}/{cap}). Upgrade to continue.",
            )


def consume(db: Session, user: User, feature: str, amount: int = 1, tokens: int = 0) -> None:
    """Increment usage, refusing to cross the cap.

    The earlier check-then-write let two concurrent requests both pass
    ``assert_within_limit`` and both increment, so the cap is re-tested here
    inside the same transaction as the write.
    """
    cap = limits_for(user).get(feature)
    period = period_key()
    for attempt in range(2):
        rec = (
            db.query(UsageRecord)
            .filter_by(user_id=user.id, feature=feature, period=period)
            .with_for_update(nowait=False)
            .first()
            if _supports_row_lock(db)
            else db.query(UsageRecord).filter_by(user_id=user.id, feature=feature, period=period).first()
        )
        if rec is None:
            db.add(
                UsageRecord(
                    user_id=user.id, feature=feature, period=period, count=amount, tokens=tokens
                )
            )
            try:
                db.commit()
                return
            except IntegrityError:
                # Another request inserted the same row first; re-read and add.
                db.rollback()
                if attempt == 0:
                    continue
                raise
        if isinstance(cap, int) and rec.count + amount > cap:
            db.rollback()
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"{(user.plan or 'free').title()} plan limit reached for "
                f"{feature.replace('_', ' ')} ({rec.count}/{cap}). Upgrade to continue.",
            )
        rec.count += amount
        rec.tokens += tokens
        db.commit()
        return


def _supports_row_lock(db: Session) -> bool:
    """SQLite has no SELECT … FOR UPDATE; Postgres does."""
    return db.bind is not None and db.bind.dialect.name == "postgresql"


def usage_snapshot(db: Session, user: User) -> dict:
    limits = limits_for(user)
    out = {}
    for feat in METERED_FEATURES:
        out[feat] = {"used": get_usage(db, user.id, feat), "limit": limits.get(feat)}
    out["plan"] = user.plan
    out["templates"] = limits["templates"]
    out["docx_export"] = limits["docx_export"]
    out["career_memory"] = limits["career_memory"]
    out["advanced_analysis"] = limits["advanced_analysis"]
    out["voice_interviews"] = limits["voice_interviews"]
    out["active_resumes"] = limits["active_resumes"]
    out["card_last4"] = getattr(user, "card_last4", "") or ""
    out["card_brand"] = getattr(user, "card_brand", "") or ""
    return out
