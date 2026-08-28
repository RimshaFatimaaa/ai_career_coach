"""Personalized reminders from roadmaps, interviews, and custom notes."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import InterviewSession, Reminder, Roadmap, User

# One generate call should never bury the user in reminders.
MAX_GENERATED_PER_RUN = 20

_WEEKDAY_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_WEEK_DAY_LABEL = re.compile(r"week\s*(\d+)\s*[·:,-]?\s*([A-Za-z]+)?", re.IGNORECASE)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_task_deadline(raw: str, anchor: datetime) -> datetime | None:
    """Resolve a roadmap deadline to a real date.

    Roadmap tasks store human labels like "Week 3 · Thursday", which
    `fromisoformat` cannot read — every reminder used to collapse onto the same
    fallback date. `anchor` is the roadmap start, so week 1 Monday is the first
    Monday on or after it.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return _aware(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        pass
    match = _WEEK_DAY_LABEL.search(raw)
    if not match:
        return None
    week = max(1, int(match.group(1)))
    weekday = _WEEKDAY_INDEX.get((match.group(2) or "monday").strip().lower(), 0)
    start = _aware(anchor) or datetime.now(timezone.utc)
    week_start = start + timedelta(days=(week - 1) * 7)
    shift = (weekday - week_start.weekday()) % 7
    return (week_start + timedelta(days=shift)).replace(hour=18, minute=0, second=0, microsecond=0)


def _out(row: Reminder) -> dict[str, Any]:
    due = _aware(row.due_at)
    now = datetime.now(timezone.utc)
    return {
        "id": row.id,
        "title": row.title,
        "body": row.body,
        "due_at": row.due_at,
        "source": row.source,
        "source_ref": row.source_ref,
        "done": row.done,
        "created_at": row.created_at,
        "overdue": bool(due and not row.done and due < now),
    }


def list_reminders(db: Session, user: User, include_done: bool = False) -> list[dict[str, Any]]:
    q = db.query(Reminder).filter_by(user_id=user.id)
    if not include_done:
        q = q.filter_by(done=False)
    rows = q.order_by(Reminder.created_at.desc()).all()
    rows.sort(key=lambda r: (r.due_at is None, r.due_at or r.created_at))
    return [_out(r) for r in rows]


def add_reminder(db: Session, user: User, title: str, body: str = "", due_at: datetime | None = None, source: str = "custom", source_ref: str = "") -> Reminder:
    row = Reminder(user_id=user.id, title=title[:255], body=body, due_at=due_at, source=source, source_ref=source_ref)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def generate_from_activity(db: Session, user: User) -> list[dict[str, Any]]:
    """Create missing reminders from open roadmap tasks and weak interviews."""
    created = 0
    existing = {(r.source, r.source_ref) for r in db.query(Reminder).filter_by(user_id=user.id, done=False).all()}
    now = datetime.now(timezone.utc)
    # Saved roadmaps first, then most recent — a capped run should reflect the
    # plans the user actually cares about.
    roadmaps = (
        db.query(Roadmap)
        .filter_by(user_id=user.id)
        .order_by(Roadmap.is_saved.desc(), Roadmap.updated_at.desc())
        .all()
    )
    pending: list[tuple[datetime, str, str, str]] = []
    for roadmap in roadmaps:
        anchor = _aware(roadmap.created_at) or now
        for mi, milestone in enumerate(roadmap.milestones or []):
            for task in milestone.get("tasks") or []:
                if task.get("completed"):
                    continue
                ref = f"roadmap:{roadmap.id}:{task.get('id')}"
                if ("roadmap", ref) in existing:
                    continue
                due = parse_task_deadline(str(task.get("deadline") or ""), anchor)
                if due is None:
                    due = now + timedelta(days=5 + mi)
                pending.append(
                    (
                        due,
                        ref,
                        str(task.get("title") or task.get("skill") or "Roadmap task"),
                        str(task.get("objective") or task.get("exercise") or "Continue this roadmap item."),
                    )
                )
                existing.add(("roadmap", ref))

    # Soonest first, so the cap keeps what is actually due next.
    pending.sort(key=lambda item: item[0])
    for due, ref, title, body in pending[:MAX_GENERATED_PER_RUN]:
        add_reminder(db, user, title=title, body=body, due_at=due, source="roadmap", source_ref=ref)
        created += 1
    weak = (
        db.query(InterviewSession)
        .filter_by(user_id=user.id, status="completed")
        .order_by(InterviewSession.completed_at.desc())
        .limit(3)
        .all()
    )
    for session in weak:
        if session.overall_score is None or session.overall_score >= 70:
            continue
        ref = f"interview:{session.id}"
        if ("interview", ref) in existing:
            continue
        add_reminder(
            db,
            user,
            title=f"Rehearse {session.target_role} interview",
            body="Your last mock was below 70. Run another session focusing on STAR structure.",
            due_at=now + timedelta(days=2),
            source="interview",
            source_ref=ref,
        )
        created += 1
    return list_reminders(db, user)
