from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.deps import CurrentUser, DbDep
from app.models import User
from app.schemas import PlanCheckoutIn, PlanConfirmIn
from app.services.billing import PLAN_LIMITS, usage_snapshot
from app.services.cards import parse_exp, validate_card
from app.services.checkout import (
    apply_plan,
    price_id_for,
    require_password,
    stripe_client,
)
from app.services.llm import gateway

router = APIRouter(prefix="/api/billing", tags=["billing"])
settings = get_settings()


@router.get("/usage")
def usage(user: CurrentUser, db: DbDep):
    snap = usage_snapshot(db, user)
    snap["stripe_enabled"] = settings.stripe_enabled
    snap["providers"] = gateway.providers()
    return snap


@router.post("/checkout")
def checkout(payload: PlanCheckoutIn, user: CurrentUser, db: DbDep):
    """Paid plans require a valid card. Downgrade to Free still needs the account password."""
    if payload.plan not in PLAN_LIMITS:
        raise HTTPException(400, "Unknown plan")
    if payload.plan == user.plan:
        return {"plan": user.plan, "status": "current"}
    if payload.plan == "free":
        require_password(user, payload.password)
        apply_plan(db, user, "free")
        return {"plan": "free", "status": "downgraded", "note": "You are back on Free. Paid features are locked."}

    stripe = stripe_client()
    price = price_id_for(payload.plan)
    if stripe and price:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user.email,
            client_reference_id=str(user.id),
            line_items=[{"price": price, "quantity": 1}],
            success_url=f"{settings.frontend_url}/app/settings?checkout=success",
            cancel_url=f"{settings.frontend_url}/app/settings?checkout=cancel",
            metadata={"user_id": str(user.id), "plan": payload.plan},
        )
        if session.customer:
            user.stripe_customer_id = str(session.customer)
            db.commit()
        return {"status": "stripe", "checkout_url": session.url}

    month, year = payload.exp_month, payload.exp_year
    if payload.exp:
        month, year = parse_exp(payload.exp)
    info = validate_card(payload.card_name, payload.card_number, month, year, payload.cvc)
    apply_plan(db, user, payload.plan, card_last4=info.last4, card_brand=info.brand)
    return {
        "plan": user.plan,
        "status": "activated",
        "card_last4": info.last4,
        "card_brand": info.brand,
        "note": f"{info.brand.title()} ending in {info.last4} was accepted. You are on {payload.plan}.",
    }


@router.post("/confirm")
def confirm(_payload: PlanConfirmIn, user: CurrentUser):
    raise HTTPException(
        400,
        "Paid plans now require a valid card. Open Settings and enter card details to upgrade.",
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: DbDep):
    stripe = stripe_client()
    if not stripe:
        raise HTTPException(503, "Stripe is not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(400, "Invalid webhook") from exc
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata") or {}
        uid = int(meta.get("user_id") or session.get("client_reference_id") or 0)
        plan = meta.get("plan")
        found = db.get(User, uid) if uid else None
        if found and plan in PLAN_LIMITS:
            found.plan = plan
            if session.get("customer"):
                found.stripe_customer_id = str(session["customer"])
            db.commit()
    return {"ok": True}
