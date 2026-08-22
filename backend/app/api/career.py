from fastapi import APIRouter, HTTPException

from sqlalchemy.orm.attributes import flag_modified

from app.agents.career import (
    analyze_skill_gap,
    build_roadmap,
    career_reply,
    compare_roles,
    extract_memories,
    fit_breakdown,
    readiness_from_gaps,
    skill_focus_rows,
)
from app.agents.graph import classify_intent, run_career_chat
from app.deps import CurrentUser, DbDep
from app.models import Conversation, Roadmap
from app.schemas import ChatIn, RoadmapIn, RoadmapTaskPatch, SkillGapIn
from app.services.billing import limits_for
from app.services.catalog import collect_profile_skills, get_role, is_catalog_role, roadmap_catalog_mismatch
from app.services.profile import ensure_profile, maybe_store_memory, memory_text, profile_to_text, recompute_scores
from app.services.rag import format_context, retrieve

router = APIRouter(prefix="/api/career", tags=["career"])


@router.post("/chat")
def chat(payload: ChatIn, user: CurrentUser, db: DbDep):
    profile = ensure_profile(db, user)
    convo = None
    if payload.conversation_id:
        convo = db.query(Conversation).filter_by(id=payload.conversation_id, user_id=user.id).first()
    if not convo:
        convo = Conversation(user_id=user.id, messages=[])
        db.add(convo)
        db.commit()
        db.refresh(convo)
    hits = retrieve(db, payload.message, k=3, category=None)
    state = run_career_chat(
        {
            "user_id": user.id,
            "message": payload.message,
            "profile_text": profile_to_text(user, profile),
            "memory_text": memory_text(db, user.id),
            "rag_context": format_context(hits),
            "intent": classify_intent(payload.message),
            "plan": user.plan,
            "advanced": bool(limits_for(user).get("advanced_analysis")),
            "history": list(convo.messages or [])[-12:],
        }
    )
    messages = list(convo.messages or [])
    messages.append({"role": "user", "content": payload.message})
    messages.append({"role": "assistant", "content": state.get("reply")})
    convo.messages = messages
    flag_modified(convo, "messages")
    convo.title = payload.message[:72]
    db.commit()
    saved_memories = []
    if limits_for(user).get("career_memory"):
        for mem in extract_memories(payload.message):
            maybe_store_memory(db, user, mem["key"], mem["value"], mem["category"])
            saved_memories.append(mem)
    return {
        "conversation_id": convo.id,
        "reply": state.get("reply"),
        "intent": state.get("intent"),
        "demo": state.get("demo"),
        "sources": hits,
        "saved_memories": saved_memories,
        "disclaimer": "Career guidance is personalized to your profile and is not a guarantee of outcomes.",
    }


@router.get("/conversations")
def list_convos(user: CurrentUser, db: DbDep):
    rows = (
        db.query(Conversation)
        .filter_by(user_id=user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(20)
        .all()
    )
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at} for c in rows]


@router.get("/conversations/{cid}")
def get_convo(cid: int, user: CurrentUser, db: DbDep):
    convo = db.query(Conversation).filter_by(id=cid, user_id=user.id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    return {"id": convo.id, "title": convo.title, "messages": convo.messages}


@router.delete("/conversations/{cid}")
def delete_convo(cid: int, user: CurrentUser, db: DbDep):
    convo = db.query(Conversation).filter_by(id=cid, user_id=user.id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    db.delete(convo)
    db.commit()
    return {"ok": True}


@router.post("/skill-gap")
def skill_gap(payload: SkillGapIn, user: CurrentUser, db: DbDep):
    profile = ensure_profile(db, user)
    owned = collect_profile_skills(profile)
    if payload.compare_role:
        result = compare_roles(owned, payload.target_role, payload.compare_role)
        return result
    gaps = analyze_skill_gap(owned, payload.target_role)
    readiness = readiness_from_gaps(gaps)
    breakdown = fit_breakdown(gaps, readiness)
    return {
        "target_role": payload.target_role,
        "role_label": get_role(payload.target_role)["label"],
        "readiness": readiness,
        "gaps": gaps,
        "fit_meaning": breakdown["formula"],
        "fit": breakdown,
        "disclaimer": "Readiness is an AI-generated estimate for personal tracking, not a hiring guarantee.",
    }


def _is_skill_plan(gaps: list) -> bool:
    return any(isinstance(g, dict) and (g.get("mode") == "skill" or g.get("target") == "Skill focus") for g in (gaps or []))


def _refresh_stale_roadmap(db, row: Roadmap, user) -> Roadmap:
    if _is_skill_plan(row.skill_gap or []):
        return row
    if not is_catalog_role(row.target_role or ""):
        return row
    if not roadmap_catalog_mismatch(row.target_role, row.skill_gap or []):
        return row
    profile = ensure_profile(db, user)
    owned = collect_profile_skills(profile)
    gaps = analyze_skill_gap(owned, row.target_role)
    row.skill_gap = gaps
    row.milestones = build_roadmap(gaps, row.duration_months, row.target_role)
    flag_modified(row, "skill_gap")
    flag_modified(row, "milestones")
    db.commit()
    db.refresh(row)
    return row


@router.post("/roadmap")
def create_roadmap(payload: RoadmapIn, user: CurrentUser, db: DbDep):
    topic = (payload.focus_skill or payload.target_role or "").strip()
    if not topic:
        raise HTTPException(400, "Enter a skill or career to plan for.")
    unit = (payload.duration_unit or "months").strip().lower()
    value = payload.duration_value if payload.duration_value else payload.duration_months
    if is_catalog_role(topic):
        profile = ensure_profile(db, user)
        owned = collect_profile_skills(profile)
        gaps = analyze_skill_gap(owned, topic)
        title = topic
        focus = ""
    else:
        gaps = skill_focus_rows(topic)
        title = topic
        focus = topic
    months_store = value if unit.startswith("month") else max(1, (value + 3) // 4 if unit.startswith("week") else max(1, (value + 19) // 20))
    milestones = build_roadmap(
        gaps,
        duration_months=payload.duration_months,
        target_role=topic,
        focus_skill=focus,
        duration_unit=unit,
        duration_value=value,
    )
    row = Roadmap(
        user_id=user.id,
        target_role=title,
        duration_months=months_store,
        milestones=milestones,
        skill_gap=gaps,
        is_saved=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    recompute_scores(db, user)
    return _roadmap_out(row)


@router.get("/roadmap")
def list_roadmaps(user: CurrentUser, db: DbDep, saved: bool = False):
    q = db.query(Roadmap).filter_by(user_id=user.id)
    if saved:
        q = q.filter_by(is_saved=True)
    rows = q.order_by(Roadmap.updated_at.desc()).all()
    return [_roadmap_out(_refresh_stale_roadmap(db, r, user)) for r in rows]


@router.post("/roadmap/{rid}/save")
def save_roadmap(rid: int, user: CurrentUser, db: DbDep):
    row = db.query(Roadmap).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Roadmap not found")
    row.is_saved = True
    db.commit()
    db.refresh(row)
    return _roadmap_out(row)


@router.delete("/roadmap/{rid}")
def delete_roadmap(rid: int, user: CurrentUser, db: DbDep):
    row = db.query(Roadmap).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Roadmap not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/roadmap/{rid}")
def get_roadmap(rid: int, user: CurrentUser, db: DbDep):
    row = db.query(Roadmap).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Roadmap not found")
    return _roadmap_out(_refresh_stale_roadmap(db, row, user))


@router.patch("/roadmap/{rid}/tasks")
def patch_task(rid: int, payload: RoadmapTaskPatch, user: CurrentUser, db: DbDep):
    row = db.query(Roadmap).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Roadmap not found")
    milestones = list(row.milestones or [])
    if payload.milestone_index >= len(milestones):
        raise HTTPException(400, "Invalid milestone")
    milestone = dict(milestones[payload.milestone_index])
    tasks = list(milestone.get("tasks") or [])
    action = payload.action or ("complete" if payload.completed is not None else None)
    if action == "add":
        skill = (payload.custom_text or "this skill").strip()
        weeks = max(1, len(milestones))
        gaps = skill_focus_rows(skill)
        row.target_role = skill
        row.skill_gap = gaps
        row.milestones = build_roadmap(
            gaps,
            duration_months=row.duration_months,
            target_role=skill,
            focus_skill=skill,
            duration_unit="weeks",
            duration_value=weeks,
        )
        flag_modified(row, "milestones")
        flag_modified(row, "skill_gap")
        db.commit()
        recompute_scores(db, user)
        return _roadmap_out(row)
    else:
        found = False
        new_tasks = []
        for t in tasks:
            if t.get("id") != payload.task_id:
                new_tasks.append(t)
                continue
            found = True
            if action == "remove":
                continue
            t = dict(t)
            if payload.completed is not None:
                t["completed"] = payload.completed
            if payload.deadline is not None:
                t["deadline"] = payload.deadline
            new_tasks.append(t)
        if not found and action != "add":
            raise HTTPException(404, "Task not found")
        tasks = new_tasks
    milestone["tasks"] = tasks
    milestones[payload.milestone_index] = milestone
    row.milestones = milestones
    flag_modified(row, "milestones")
    db.commit()
    recompute_scores(db, user)
    return _roadmap_out(row)


def _roadmap_out(row: Roadmap) -> dict:
    tasks = [t for m in (row.milestones or []) for t in m.get("tasks", [])]
    done = sum(1 for t in tasks if t.get("completed"))
    label = ""
    if row.milestones:
        label = str((row.milestones[0] or {}).get("duration_label") or "")
    return {
        "id": row.id,
        "target_role": row.target_role,
        "duration_months": row.duration_months,
        "duration_label": label or f"{row.duration_months} month plan",
        "milestones": row.milestones,
        "skill_gap": row.skill_gap,
        "progress": {"done": done, "total": len(tasks)},
        "is_saved": bool(getattr(row, "is_saved", False)),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
