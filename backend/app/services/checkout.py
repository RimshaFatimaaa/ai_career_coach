"""Checkout: valid card for paid plans, password for downgrade. Stripe hosted checkout when configured."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.services.auth import verify_password
from app.services.billing import PLAN_LIMITS

settings = get_settings()

PLAN_PRICES = {"pro": 1299, "premium": 2999}  # cents, display only when Stripe prices unset


def require_password(user: User, password: str) -> None:
    if not password or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Re-enter your account password to change plans.")


def make_intent(user: User, plan: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=12)
    return jwt.encode(
        {"sub": str(user.id), "plan": plan, "typ": "plan_intent", "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )


def read_intent(token: str, user: User) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(400, "Plan confirmation expired. Start again.") from exc
    if payload.get("typ") != "plan_intent" or int(payload.get("sub") or 0) != user.id:
        raise HTTPException(400, "Invalid plan confirmation.")
    plan = str(payload.get("plan") or "")
    if plan not in PLAN_LIMITS:
        raise HTTPException(400, "Unknown plan")
    return plan


def apply_plan(db: Session, user: User, plan: str, card_last4: str = "", card_brand: str = "") -> User:
    user.plan = plan
    if card_last4:
        user.card_last4 = card_last4
        user.card_brand = card_brand
    if plan == "free":
        user.card_last4 = ""
        user.card_brand = ""
    db.commit()
    db.refresh(user)
    return user


def stripe_client():
    if not settings.stripe_enabled:
        return None
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


def price_id_for(plan: str) -> str:
    if plan == "pro":
        return settings.stripe_price_pro
    if plan == "premium":
        return settings.stripe_price_premium
    return ""
