from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbDep
from app.models import CareerMemory, User
from app.schemas import MemoryIn, MemoryUpdateIn
from app.services.billing import limits_for

router = APIRouter(prefix="/api/memory", tags=["memory"])

UPGRADE_MESSAGE = "Career memory is available on Pro and Premium"


def require_memory_plan(user: User) -> None:
    """Career memory is a paid feature on every path, not just on create.

    Reading and editing were previously open, which left the whole feature
    usable on Free — including for users who had downgraded from Pro.
    """
    if not limits_for(user).get("career_memory"):
        raise HTTPException(402, UPGRADE_MESSAGE)


def _out(row: CareerMemory) -> dict:
    return {
        "id": row.id,
        "category": row.category,
        "key": row.key,
        "value": row.value,
        "enabled": row.enabled,
        "updated_at": row.updated_at,
    }


@router.get("")
def list_memory(user: CurrentUser, db: DbDep):
    require_memory_plan(user)
    rows = db.query(CareerMemory).filter_by(user_id=user.id).order_by(CareerMemory.updated_at.desc()).all()
    return [_out(m) for m in rows]


@router.post("")
def create_memory(payload: MemoryIn, user: CurrentUser, db: DbDep):
    require_memory_plan(user)
    key = payload.key.strip()
    # Upsert, matching what the coach does internally. Two rows with the same
    # key would both be injected into the prompt and could contradict.
    row = db.query(CareerMemory).filter_by(user_id=user.id, key=key).first()
    if row:
        row.category = payload.category
        row.value = payload.value
        row.enabled = payload.enabled
    else:
        row = CareerMemory(
            user_id=user.id,
            category=payload.category,
            key=key,
            value=payload.value,
            enabled=payload.enabled,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/{mid}")
def update_memory(mid: int, payload: MemoryUpdateIn, user: CurrentUser, db: DbDep):
    require_memory_plan(user)
    row = db.query(CareerMemory).filter_by(id=mid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Memory not found")
    if payload.value is not None:
        row.value = payload.value
    if payload.enabled is not None:
        row.enabled = payload.enabled
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/{mid}")
def delete_memory(mid: int, user: CurrentUser, db: DbDep):
    # Deletion stays open so a downgraded user can still remove their own data.
    row = db.query(CareerMemory).filter_by(id=mid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Memory not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
