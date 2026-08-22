from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbDep
from app.models import CareerMemory
from app.schemas import MemoryIn, MemoryUpdateIn
from app.services.billing import limits_for

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("")
def list_memory(user: CurrentUser, db: DbDep):
    rows = db.query(CareerMemory).filter_by(user_id=user.id).order_by(CareerMemory.updated_at.desc()).all()
    return [
        {
            "id": m.id,
            "category": m.category,
            "key": m.key,
            "value": m.value,
            "enabled": m.enabled,
            "updated_at": m.updated_at,
        }
        for m in rows
    ]


@router.post("")
def create_memory(payload: MemoryIn, user: CurrentUser, db: DbDep):
    if not limits_for(user).get("career_memory"):
        raise HTTPException(402, "Career memory is available on Pro and Premium")
    row = CareerMemory(
        user_id=user.id,
        category=payload.category,
        key=payload.key,
        value=payload.value,
        enabled=payload.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "category": row.category, "key": row.key, "value": row.value, "enabled": row.enabled}


@router.patch("/{mid}")
def update_memory(mid: int, payload: MemoryUpdateIn, user: CurrentUser, db: DbDep):
    row = db.query(CareerMemory).filter_by(id=mid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Memory not found")
    if payload.value is not None:
        row.value = payload.value
    if payload.enabled is not None:
        row.enabled = payload.enabled
    db.commit()
    return {"id": row.id, "category": row.category, "key": row.key, "value": row.value, "enabled": row.enabled}


@router.delete("/{mid}")
def delete_memory(mid: int, user: CurrentUser, db: DbDep):
    row = db.query(CareerMemory).filter_by(id=mid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Memory not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
