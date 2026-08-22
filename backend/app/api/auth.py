from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.deps import CurrentUser, DbDep
from app.models import User
from app.schemas import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, TokenOut
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.mail import send_mail
from app.services.profile import ensure_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "plan": user.plan,
    }


def _token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: DbDep):
    if not payload.accept_terms:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accept the terms of service to create an account.")
    if db.query(User).filter_by(email=payload.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_profile(db, user)
    return TokenOut(access_token=create_access_token(user.id), user=_user_dict(user))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: DbDep):
    user = db.query(User).filter_by(email=payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id), user=_user_dict(user))


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, db: DbDep):
    generic = {"ok": True, "message": "If that email is registered, we sent reset instructions."}
    user = db.query(User).filter_by(email=payload.email.lower()).first()
    if not user:
        return generic
    token = token_urlsafe(32)
    user.password_reset_token_hash = _token_hash(token)
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    sent = send_mail(
        user.email,
        "Reset your Atelier password",
        f"Reset your password using this link (valid for 1 hour):\n\n{reset_url}\n\n"
        "If you did not request this, you can ignore the email.",
    )
    out = dict(generic)
    if settings.app_env == "development" and not sent:
        out["reset_url"] = reset_url
        out["message"] = "No email server is configured. Use this reset link (development only)."
    return out


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: DbDep):
    digest = _token_hash(payload.token.strip())
    user = db.query(User).filter_by(password_reset_token_hash=digest).first()
    expires = _aware(user.password_reset_expires) if user else None
    if not user or not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")
    user.password_hash = hash_password(payload.password)
    user.password_reset_token_hash = ""
    user.password_reset_expires = None
    db.commit()
    return {"ok": True, "message": "Password updated. You can sign in now."}


@router.get("/me")
def me(user: CurrentUser):
    return _user_dict(user)
