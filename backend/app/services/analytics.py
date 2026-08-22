"""Phase 3 advanced career analytics from stored activity."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import InterviewSession, Resume, Roadmap, User
from app.services.profile import ensure_profile, recompute_scores
from app.services.voice import aggregate_voice


def analytics_payload(db: Session, user: User) -> dict[str, Any]:
    profile = recompute_scores(db, user)
    interviews = (
        db.query(InterviewSession)
        .filter_by(user_id=user.id)
        .order_by(InterviewSession.created_at.asc())
        .all()
    )
    completed = [s for s in interviews if s.status == "completed"]
    interview_history = [
        {
            "id": s.id,
            "date": s.completed_at or s.created_at,
            "role": s.target_role,
            "mode": getattr(s, "mode", "text") or "text",
            "score": s.overall_score,
            "type": s.interview_type,
        }
        for s in completed
        if s.overall_score is not None
    ]
    scores = [h["score"] for h in interview_history]
    trend = None
    if len(scores) >= 2:
        trend = "up" if scores[-1] > scores[0] else "down" if scores[-1] < scores[0] else "flat"

    strengths: dict[str, int] = defaultdict(int)
    weaknesses: dict[str, int] = defaultdict(int)
    voice_rows = []
    for s in completed:
        report = s.report or {}
        for item in report.get("strengths") or []:
            strengths[str(item)] += 1
        for item in report.get("weaknesses") or []:
            weaknesses[str(item)] += 1
        if report.get("voice"):
            voice_rows.append(report["voice"])
        elif s.questions:
            agg = aggregate_voice(s.questions or [])
            if agg:
                voice_rows.append(agg)

    resumes = db.query(Resume).filter_by(user_id=user.id, is_active=True).all()
    ats_history = []
    for r in resumes:
        ats = r.last_ats if isinstance(r.last_ats, dict) else None
        if ats and ats.get("had_jd"):
            ats_history.append(
                {
                    "resume_id": r.id,
                    "title": r.title,
                    "ats_readiness": ats.get("ats_readiness"),
                    "keyword_alignment": ats.get("keyword_alignment"),
                    "updated_at": r.updated_at,
                }
            )

    roadmap = (
        db.query(Roadmap).filter_by(user_id=user.id).order_by(Roadmap.updated_at.desc()).first()
    )
    gap_mix = {"high": 0, "medium": 0, "low": 0, "none": 0}
    if roadmap:
        for g in roadmap.skill_gap or []:
            key = str(g.get("gap") or "none")
            if key not in gap_mix:
                key = "none"
            gap_mix[key] += 1
        tasks = [t for m in (roadmap.milestones or []) for t in m.get("tasks", [])]
        task_total = len(tasks)
        task_done = sum(1 for t in tasks if t.get("completed"))
    else:
        task_total = 0
        task_done = 0

    top_strengths = sorted(strengths.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top_weaknesses = sorted(weaknesses.items(), key=lambda kv: kv[1], reverse=True)[:5]
    avg_voice = None
    if voice_rows:
        avg_voice = {
            "avg_wpm": round(sum(float(v.get("avg_words_per_minute") or v.get("words_per_minute") or 0) for v in voice_rows) / len(voice_rows), 1),
            "avg_filler_rate": round(sum(float(v.get("avg_filler_rate") or v.get("filler_rate") or 0) for v in voice_rows) / len(voice_rows), 1),
            "sessions": len(voice_rows),
        }

    return {
        "readiness": profile.readiness_score,
        "resume_health": profile.resume_health,
        "interview_performance": profile.interview_performance,
        "interview_history": interview_history[-12:],
        "interview_trend": trend,
        "interview_count": len(completed),
        "avg_interview": round(sum(scores) / len(scores), 1) if scores else 0,
        "best_interview": max(scores) if scores else 0,
        "top_strengths": [{"label": k, "count": n} for k, n in top_strengths],
        "top_weaknesses": [{"label": k, "count": n} for k, n in top_weaknesses],
        "ats_history": ats_history[-8:],
        "skill_gap_mix": gap_mix,
        "roadmap_progress": {"done": task_done, "total": task_total},
        "voice": avg_voice,
        "disclaimer": "Analytics are coaching estimates from your Atelier activity, not a hiring prediction.",
    }
