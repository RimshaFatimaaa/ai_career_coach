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


def plan_from_price_id(price_id: str) -> str | None:
    if not price_id:
        return None
    if price_id == settings.stripe_price_pro:
        return "pro"
    if price_id == settings.stripe_price_premium:
        return "premium"
    return None


def _stripe_get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def plan_from_subscription(sub: dict | None) -> str | None:
    """Map a Stripe subscription object to a local plan. None means leave the current plan."""
    if not sub:
        return None
    status = str(_stripe_get(sub, "status") or "").lower()
    if status in {"canceled", "unpaid", "incomplete_expired"}:
        return "free"
    items = _stripe_get(sub, "items") or {}
    data = _stripe_get(items, "data") or []
    if not data:
        return None
    price = _stripe_get(data[0], "price") or {}
    price_id = _stripe_get(price, "id") if not isinstance(price, str) else price
    mapped = plan_from_price_id(str(price_id or ""))
    if mapped:
        return mapped
    if status in {"active", "trialing"}:
        return None
    return "free"


def find_user_for_stripe(db: Session, *, user_id: int = 0, customer_id: str = "") -> User | None:
    if user_id:
        found = db.get(User, user_id)
        if found:
            return found
    cid = (customer_id or "").strip()
    if cid:
        return db.query(User).filter_by(stripe_customer_id=cid).first()
    return None


def _cancel_subscription(stripe, sid: str) -> None:
    try:
        stripe.Subscription.cancel(sid)
        return
    except Exception:
        stripe.Subscription.delete(sid)


def cancel_stripe_billing(user: User, *, required: bool = False, delete_customer: bool = False) -> None:
    """Stop Stripe charges for this user. Does nothing when Stripe is unset or no customer id."""
    stripe = stripe_client()
    cid = (getattr(user, "stripe_customer_id", "") or "").strip()
    if not stripe or not cid:
        return
    try:
        subs = stripe.Subscription.list(customer=cid, status="all", limit=100)
        for sub in _stripe_get(subs, "data") or []:
            status = str(_stripe_get(sub, "status") or "").lower()
            sid = _stripe_get(sub, "id")
            if not sid or status in {"canceled", "incomplete_expired"}:
                continue
            _cancel_subscription(stripe, str(sid))
        if delete_customer:
            try:
                stripe.Customer.delete(cid)
            except Exception:
                pass
    except HTTPException:
        raise
    except Exception:
        if required:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Could not cancel the Stripe subscription. Try again or contact support.",
            ) from None
