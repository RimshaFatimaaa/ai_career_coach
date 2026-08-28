import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.career import router as career_router
from app.api.integrations import router as integrations_router
from app.api.interview import router as interview_router
from app.api.mcp import router as mcp_router
from app.api.memory import router as memory_router
from app.api.profile import router as profile_router
from app.api.resume import router as resume_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine, migrate_schema
from app.models import User
from app.ratelimit import limiter
from app.services.auth import hash_password
from app.services.llm import gateway
from app.services.rag import ingest_knowledge

settings = get_settings()
log = logging.getLogger("uvicorn.error")

# Superseded by settings.admin_email. Older databases still carry this address,
# which pydantic's EmailStr rejects, so the account could never sign in.
LEGACY_ADMIN_EMAIL = "admin@careercoach.local"


def seed_admin(db) -> None:
    email = settings.admin_email.strip().lower()
    password = settings.seed_admin_password
    legacy = db.query(User).filter_by(email=LEGACY_ADMIN_EMAIL).first()
    if legacy and not db.query(User).filter_by(email=email).first():
        legacy.email = email
        if password:
            legacy.password_hash = hash_password(password)
        db.commit()
        log.warning("Renamed the legacy admin account to %s so it can sign in.", email)
        return
    existing = db.query(User).filter_by(email=email).first()
    if existing:
        if existing.role != "admin":
            log.error(
                "ADMIN_EMAIL %s is already a non-admin account. Set a different ADMIN_EMAIL; "
                "refusing to promote a squatted address.",
                email,
            )
        return
    if not password:
        log.warning(
            "No ADMIN_PASSWORD set and APP_ENV is %s — skipping admin seed. "
            "Set ADMIN_EMAIL and ADMIN_PASSWORD to create one.",
            settings.app_env,
        )
        return
    db.add(
        User(
            email=email,
            password_hash=hash_password(password),
            full_name="Platform Admin",
            role="admin",
            plan="premium",
        )
    )
    db.commit()
    if not settings.admin_password:
        log.warning(
            "Seeded development admin %s with the documented default password. "
            "Set ADMIN_PASSWORD before deploying.",
            email,
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    problem = settings.secret_key_problem
    if problem:
        raise RuntimeError(
            f"Refusing to start with APP_ENV={settings.app_env}: {problem} "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    db = SessionLocal()
    try:
        ingest_knowledge(db)
        seed_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(career_router)
app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(memory_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(integrations_router)
app.include_router(mcp_router)


@app.get("/api/health")
def health():
    """Unauthenticated liveness probe.

    Infrastructure detail is only returned in development; production callers
    get the minimum a load balancer needs.
    """
    base = {"ok": True, "app": settings.app_name, "llm": gateway.enabled}
    if not settings.is_development:
        return base
    return {
        **base,
        "llm_model": settings.llm_model,
        "llm_error": gateway.last_error or None,
        "providers": gateway.providers(),
        "stripe": settings.stripe_enabled,
        "r2": settings.r2_enabled,
        "database": "postgres" if settings.is_postgres else "sqlite",
        "supabase_url": settings.supabase_url or None,
        "smtp": settings.smtp_enabled,
        "env": settings.app_env,
        "phase3": ["linkedin_github", "mcp", "analytics", "reminders"],
    }
