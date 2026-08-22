from fastapi import APIRouter, HTTPException

from app.deps import AdminUser, DbDep
from app.models import InterviewSession, KnowledgeDoc, UsageRecord, User
from app.schemas import AdminPlanIn
from app.services.billing import PLAN_LIMITS
from app.services.checkout import apply_plan, require_password
from app.services.llm import gateway

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/admin/overview")
def admin_overview(_: AdminUser, db: DbDep):
    users = db.query(User).count()
    plans = {p: db.query(User).filter_by(plan=p).count() for p in ("free", "pro", "premium")}
    interviews = db.query(InterviewSession).count()
    knowledge = db.query(KnowledgeDoc).count()
    tokens = sum(r.tokens for r in db.query(UsageRecord).all())
    return {
        "users": users,
        "plans": plans,
        "interviews": interviews,
        "knowledge_chunks": knowledge,
        "recorded_tokens": tokens,
        "llm_enabled": gateway.enabled,
        "providers": gateway.providers(),
        "note": "Admins do not get automatic access to private resume files.",
    }


@router.get("/admin/users")
def admin_users(_: AdminUser, db: DbDep):
    rows = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "plan": u.plan,
            "role": u.role,
            "created_at": u.created_at,
        }
        for u in rows
    ]


@router.post("/admin/users/{uid}/plan")
def admin_set_plan(uid: int, payload: AdminPlanIn, admin: AdminUser, db: DbDep):
    require_password(admin, payload.password)
    if payload.plan not in PLAN_LIMITS:
        raise HTTPException(400, "Unknown plan")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(404, "User not found")
    apply_plan(db, user, payload.plan)
    return {"id": user.id, "plan": user.plan}
