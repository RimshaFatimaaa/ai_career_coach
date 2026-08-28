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
from app.schemas import ChatIn, MemoryConfirmIn, RoadmapIn, RoadmapTaskPatch, SkillGapIn
from app.services.billing import assert_within_limit, consume, limits_for
from app.services.catalog import collect_profile_skills, get_role, is_catalog_role, roadmap_catalog_mismatch
from app.services.profile import ensure_profile, maybe_store_memory, memory_text, profile_to_text, recompute_scores
from app.services.rag import format_context, retrieve

router = APIRouter(prefix="/api/career", tags=["career"])

DEFAULT_CONVERSATION_TITLE = "Career chat"
MAX_STORED_TURNS = 80


@router.post("/chat")
def chat(payload: ChatIn, user: CurrentUser, db: DbDep):
    message = payload.message.strip()
    if not message:
        raise HTTPException(400, "Type a question for the coach.")
    assert_within_limit(db, user, "career_chats")
    profile = ensure_profile(db, user)
    convo = None
    if payload.conversation_id:
        # Silently opening a new thread here made a stale tab look like it had
        # resumed the old conversation.
        convo = db.query(Conversation).filter_by(id=payload.conversation_id, user_id=user.id).first()
        if not convo:
            raise HTTPException(404, "That conversation no longer exists. Start a new one.")
    hits = retrieve(db, message, k=3, category=None)
    state = run_career_chat(
        {
            "user_id": user.id,
            "message": message,
            "profile_text": profile_to_text(user, profile),
            "memory_text": memory_text(db, user),
            "rag_context": format_context(hits),
            "intent": classify_intent(message),
            "plan": user.plan,
            "advanced": bool(limits_for(user).get("advanced_analysis")),
            "history": list(convo.messages or [])[-12:] if convo else [],
        }
    )
    reply = state.get("reply") or ""
    if reply.startswith("I could not reach the language model"):
        # A transport failure is not a coaching turn and is not worth a credit.
        raise HTTPException(503, "The language model could not be reached. Try again in a moment.")
    demo = bool(state.get("demo"))
    # Take the credit before writing the thread so a second request at cap-1
    # cannot persist an extra conversation after the first commit.
    if not demo:
        consume(db, user, "career_chats")
    # Created only once there is a reply to store, so a failure mid-request
    # does not leave an empty thread in the user's history.
    if convo is None:
        convo = Conversation(user_id=user.id, messages=[])
        db.add(convo)
    messages = list(convo.messages or [])
    messages.append({"role": "user", "content": message})
    messages.append({"role": "assistant", "content": state.get("reply")})
    if len(messages) > MAX_STORED_TURNS:
        messages = messages[-MAX_STORED_TURNS:]
    convo.messages = messages
    flag_modified(convo, "messages")
    # The first question names the thread; later turns must not rewrite it.
    if not convo.title or convo.title == DEFAULT_CONVERSATION_TITLE:
        convo.title = message[:72]
    db.commit()
    db.refresh(convo)

    suggested_memories = []
    if limits_for(user).get("career_memory"):
        # Offered, not stored. Saving silently on every turn contradicted the
        # promise that the coach asks before remembering something.
        suggested_memories = extract_memories(message, plan=user.plan)
    return {
        "conversation_id": convo.id,
        "reply": state.get("reply"),
        "intent": state.get("intent"),
        "demo": demo,
        "metered": not demo,
        "sources": hits,
        "suggested_memories": suggested_memories,
        "disclaimer": "Career guidance is personalized to your profile and is not a guarantee of outcomes.",
    }


@router.post("/memories/confirm")
def confirm_memories(payload: MemoryConfirmIn, user: CurrentUser, db: DbDep):
    """Persist memories the coach offered and the user accepted."""
    if not limits_for(user).get("career_memory"):
        raise HTTPException(402, "Career memory is on Pro and Premium")
    saved = []
    for mem in payload.memories:
        key = mem.key.strip()
        value = mem.value.strip()
        if not key or not value:
            continue
        maybe_store_memory(db, user, key, value, (mem.category or "direction").strip() or "direction")
        saved.append({"key": key, "value": value, "category": mem.category})
    return {"saved": saved}


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
    # A role outside the catalog costs a model call, so this is metered like
    # every other feature that can reach a provider.
    assert_within_limit(db, user, "skill_gap_analyses")
    consume(db, user, "skill_gap_analyses")
    profile = ensure_profile(db, user)
    owned = collect_profile_skills(profile)
    if payload.compare_role:
        return compare_roles(owned, payload.target_role, payload.compare_role, plan=user.plan)
    gaps = analyze_skill_gap(owned, payload.target_role, plan=user.plan)
    readiness = readiness_from_gaps(gaps)
    breakdown = fit_breakdown(gaps, readiness)
    return {
        "target_role": payload.target_role,
        "role_label": get_role(payload.target_role, plan=user.plan)["label"],
        "readiness": readiness,
        "gaps": gaps,
        "fit_meaning": breakdown["formula"],
        "fit": breakdown,
        "disclaimer": "Readiness is an AI-generated estimate for personal tracking, not a hiring guarantee.",
    }


def _is_skill_plan(gaps: list) -> bool:
    return any(isinstance(g, dict) and (g.get("mode") == "skill" or g.get("target") == "Skill focus") for g in (gaps or []))


def _merge_roadmap_progress(old_milestones: list, new_milestones: list) -> list:
    """Keep completions, deadlines, and custom tasks when the catalog is rebuilt."""
    old_by_id: dict[str, dict] = {}
    custom_by_week: dict[int, list] = {}
    for milestone in old_milestones or []:
        week = int(milestone.get("week") or milestone.get("month") or 0)
        for task in milestone.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            if (task.get("kind") or "") == "custom":
                custom_by_week.setdefault(week, []).append(dict(task))
                continue
            tid = str(task.get("id") or "")
            if tid:
                old_by_id[tid] = task
    merged = []
    for milestone in new_milestones or []:
        row = dict(milestone)
        week = int(row.get("week") or row.get("month") or 0)
        tasks = []
        for task in row.get("tasks") or []:
            item = dict(task)
            prev = old_by_id.get(str(item.get("id") or ""))
            if prev:
                item["completed"] = bool(prev.get("completed"))
                if prev.get("deadline"):
                    item["deadline"] = prev.get("deadline")
            tasks.append(item)
        for extra in custom_by_week.pop(week, []):
            tasks.append(extra)
        row["tasks"] = tasks
        merged.append(row)
    leftovers = [t for batch in custom_by_week.values() for t in batch]
    if leftovers and merged:
        last = dict(merged[-1])
        last["tasks"] = list(last.get("tasks") or []) + leftovers
        merged[-1] = last
    return merged


def _refresh_stale_roadmap(db, row: Roadmap, user) -> Roadmap:
    if _is_skill_plan(row.skill_gap or []):
        return row
    if not is_catalog_role(row.target_role or ""):
        return row
    if not roadmap_catalog_mismatch(row.target_role, row.skill_gap or []):
        return row
    profile = ensure_profile(db, user)
    owned = collect_profile_skills(profile)
    gaps = analyze_skill_gap(owned, row.target_role, plan=user.plan)
    rebuilt = build_roadmap(gaps, row.duration_months, row.target_role)
    row.skill_gap = gaps
    row.milestones = _merge_roadmap_progress(row.milestones or [], rebuilt)
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
    assert_within_limit(db, user, "roadmaps")
    consume(db, user, "roadmaps")
    unit = (payload.duration_unit or "months").strip().lower()
    value = payload.duration_value if payload.duration_value else payload.duration_months
    if is_catalog_role(topic):
        profile = ensure_profile(db, user)
        owned = collect_profile_skills(profile)
        gaps = analyze_skill_gap(owned, topic, plan=user.plan)
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
    # The lower bound matters: Python would happily let -1 edit the last week.
    if not 0 <= payload.milestone_index < len(milestones):
        raise HTTPException(400, "Invalid milestone")
    milestone = dict(milestones[payload.milestone_index])
    tasks = list(milestone.get("tasks") or [])
    action = payload.action or ("complete" if payload.completed is not None else None)
    if action == "add":
        # Appends one task to the chosen week. This used to rebuild the whole
        # roadmap and rename target_role, silently discarding the user's plan.
        skill = (payload.custom_text or "").strip()
        if not skill:
            raise HTTPException(400, "Describe the task you want to add.")
        existing_ids = {t.get("id") for m in milestones for t in (m.get("tasks") or [])}
        n = 1
        while f"m{payload.milestone_index + 1}-custom{n}" in existing_ids:
            n += 1
        tasks.append(
            {
                "id": f"m{payload.milestone_index + 1}-custom{n}",
                "title": skill[:160],
                "skill": skill[:80],
                "day": "Anytime",
                "objective": skill,
                "priority": "medium",
                "deadline": payload.deadline or milestone.get("title") or "",
                "completed": False,
                "kind": "custom",
            }
        )
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
        if not found:
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
