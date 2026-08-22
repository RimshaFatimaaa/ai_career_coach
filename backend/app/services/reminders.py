"""Personalized reminders from roadmaps, interviews, and custom notes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import InterviewSession, Reminder, Roadmap, User


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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
    roadmaps = db.query(Roadmap).filter_by(user_id=user.id).all()
    for roadmap in roadmaps:
        for mi, milestone in enumerate(roadmap.milestones or []):
            for task in milestone.get("tasks") or []:
                if task.get("completed"):
                    continue
                ref = f"roadmap:{roadmap.id}:{task.get('id')}"
                if ("roadmap", ref) in existing:
                    continue
                due = None
                raw = str(task.get("deadline") or "")
                if raw:
                    try:
                        due = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    except ValueError:
                        due = now + timedelta(days=7)
                else:
                    due = now + timedelta(days=5 + mi)
                add_reminder(
                    db,
                    user,
                    title=str(task.get("title") or task.get("skill") or "Roadmap task"),
                    body=str(task.get("objective") or task.get("exercise") or "Continue this roadmap item."),
                    due_at=due,
                    source="roadmap",
                    source_ref=ref,
                )
                created += 1
                existing.add(("roadmap", ref))
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
