from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.deps import CurrentUser, DbDep
from app.models import User, utcnow
from app.ratelimit import limiter
from app.schemas import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, TokenOut
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.mail import send_mail
from app.services.profile import ensure_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
log = logging.getLogger("uvicorn.error")


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


def _token_for(user: User) -> str:
    return create_access_token(user.id, int(user.session_epoch or 0))


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.post("/register", response_model=TokenOut)
@limiter.limit("10/hour")
def register(request: Request, payload: RegisterIn, db: DbDep):
    if not payload.accept_terms:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accept the terms of service to create an account.")
    email = payload.email.lower()
    if email == settings.admin_email.strip().lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That email is reserved.")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Could not create an account with that email.")
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        terms_accepted_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_profile(db, user)
    return TokenOut(access_token=_token_for(user), user=_user_dict(user))


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginIn, db: DbDep):
    user = db.query(User).filter_by(email=payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")
    # A new login retires every previously issued token, so a stolen session
    # dies as soon as the owner signs in again.
    user.session_epoch = int(user.session_epoch or 0) + 1
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=_token_for(user), user=_user_dict(user))


@router.post("/forgot-password")
@limiter.limit("5/hour")
def forgot_password(request: Request, payload: ForgotPasswordIn, db: DbDep):
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
    if not sent:
        # The link is a working credential, so it is only ever written out on a
        # developer machine. In a real deployment logs are widely readable and
        # printing it there would hand over any account for an hour.
        if settings.is_development:
            log.warning("No email server configured. Password reset link for %s: %s", user.email, reset_url)
        else:
            log.error(
                "Could not send the password reset email for user id %s. Configure SMTP_HOST and SMTP_FROM.",
                user.id,
            )
    return generic


@router.post("/reset-password")
@limiter.limit("10/hour")
def reset_password(request: Request, payload: ResetPasswordIn, db: DbDep):
    digest = _token_hash(payload.token.strip())
    user = db.query(User).filter_by(password_reset_token_hash=digest).first()
    expires = _aware(user.password_reset_expires) if user else None
    if not user or not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")
    user.password_hash = hash_password(payload.password)
    user.password_reset_token_hash = ""
    user.password_reset_expires = None
    user.session_epoch = int(user.session_epoch or 0) + 1
    db.commit()
    return {"ok": True, "message": "Password updated. Any other signed-in devices were logged out."}


@router.post("/logout")
def logout(user: CurrentUser, db: DbDep):
    row = db.get(User, user.id)
    if row:
        row.session_epoch = int(row.session_epoch or 0) + 1
        db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser):
    return _user_dict(user)
