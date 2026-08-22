"""Subscription limits and usage tracking — PRD §13."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import UsageRecord, User

PLAN_LIMITS = {
    "free": {
        "active_resumes": 1,
        "resume_analyses": 3,
        "resume_generations": 2,
        "tailorings": 2,
        "mock_interviews": 1,
        "interview_questions": 15,
        "cover_letters": 1,
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
        "tailorings": 15,
        "mock_interviews": 10,
        "interview_questions": 150,
        "cover_letters": 20,
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
        "tailorings": 60,
        "mock_interviews": 40,
        "interview_questions": 600,
        "cover_letters": 80,
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

FEATURE_KEYS = {
    "resume_analyses": "resume_analyses",
    "resume_generations": "resume_generations",
    "tailorings": "tailorings",
    "mock_interviews": "mock_interviews",
    "interview_questions": "interview_questions",
    "cover_letters": "cover_letters",
}


def period_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def limits_for(user: User) -> dict:
    plan = (getattr(user, "plan", None) or "free").strip().lower()
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def get_usage(db: Session, user_id: int, feature: str) -> int:
    rec = (
        db.query(UsageRecord)
        .filter_by(user_id=user_id, feature=feature, period=period_key())
        .first()
    )
    return rec.count if rec else 0


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
    rec = (
        db.query(UsageRecord)
        .filter_by(user_id=user.id, feature=feature, period=period_key())
        .first()
    )
    if rec:
        rec.count += amount
        rec.tokens += tokens
    else:
        rec = UsageRecord(
            user_id=user.id, feature=feature, period=period_key(), count=amount, tokens=tokens
        )
        db.add(rec)
    db.commit()


def usage_snapshot(db: Session, user: User) -> dict:
    limits = limits_for(user)
    features = [
        "resume_analyses",
        "resume_generations",
        "tailorings",
        "mock_interviews",
        "interview_questions",
        "cover_letters",
    ]
    out = {}
    for feat in features:
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
