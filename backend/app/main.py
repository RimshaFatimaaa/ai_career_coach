from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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
from app.services.auth import hash_password
from app.services.llm import gateway
from app.services.rag import ingest_knowledge

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    db = SessionLocal()
    try:
        ingest_knowledge(db)
        if not db.query(User).filter_by(email="admin@careercoach.local").first():
            db.add(
                User(
                    email="admin@careercoach.local",
                    password_hash=hash_password("Admin1234!"),
                    full_name="Platform Admin",
                    role="admin",
                    plan="premium",
                )
            )
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    return {
        "ok": True,
        "app": settings.app_name,
        "llm": gateway.enabled,
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
