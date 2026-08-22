"""Career, skill-gap, and roadmap agents."""

from __future__ import annotations

from typing import Any

from app.services.catalog import LEVEL_RANK, get_role, infer_level, is_catalog_role
from app.services.llm import SAFETY_PREAMBLE, gateway, wrap_untrusted

RESOURCES = {
    "python": ("Python for Everybody / official tutorial", "Build a CLI that parses a dataset", "Personal data dashboard"),
    "sql": ("Mode SQL tutorial or Select Star SQL", "Write 15 joins/window-function queries", "Analyze a public dataset end-to-end"),
    "docker": ("Docker getting started", "Containerize a FastAPI app", "Multi-service compose for an ML API"),
    "machine learning": ("Google ML Crash Course", "Train a baseline then beat it", "Kaggle-style project with a writeup"),
    "langchain / llm apps": ("LangChain docs + LangGraph tutorials", "Build a RAG chatbot over your notes", "Career-coach style multi-agent mini app"),
    "cad (autocad, revit, or similar)": ("Official Revit or AutoCAD essentials", "Redraw a small plan from a reference", "Document one room to construction-set quality"),
    "drawing and drafting": ("Freehand and measured drawing practice", "Daily 20-minute sketches", "A measured drawing of a real space"),
    "design process": ("A studio design-process primer", "Write a one-page brief then iterate 3 schemes", "A mini project from concept to boards"),
    "portfolio / body of work": ("How to sequence a portfolio", "Edit to 6–10 strongest pieces", "A PDF portfolio with captions"),
    "portfolio of built or academic work": ("How to sequence a portfolio", "Edit to 6–10 strongest pieces", "A PDF portfolio with captions"),
    "visual fundamentals (form, color, composition)": ("A foundations drawing/color course", "Still-life studies weekly", "A small series that proves the skill"),
    "typography": ("Practical typography (Bringhurst excerpts / Butterick)", "Redesign a poster with a type-only system", "A type specimen for a real brief"),
    "lesson planning": ("Your curriculum's planning guide", "Write one complete lesson with assessment", "A week of linked lessons"),
    "default": ("A reputable course or studio in this skill", "A focused weekly exercise", "A portfolio piece that proves the skill"),
}


def analyze_skill_gap(owned_skills: list[str], target_role: str) -> list[dict[str, Any]]:
    role = get_role(target_role)
    rows = []
    for skill, target in role["required"].items():
        current = infer_level(skill, owned_skills)
        gap = _gap(current, target)
        resource, exercise, project = RESOURCES.get(skill.lower(), RESOURCES["default"])
        rows.append(
            {
                "skill": skill,
                "current": current.title(),
                "target": target.title(),
                "gap": gap,
                "priority": {"high": 1, "medium": 2, "low": 3}[gap],
                "priority_label": _priority_label(gap, current),
                "why_it_matters": _explain_gap(skill, current, target, gap, role["label"]),
                "resource": resource,
                "exercise": exercise,
                "project": project,
                "recommended_proficiency": target.title(),
            }
        )
    for skill in role.get("optional", []):
        current = infer_level(skill, owned_skills)
        rows.append(
            {
                "skill": skill,
                "current": current.title() if current != "missing" else "Missing",
                "target": "Optional",
                "gap": "low",
                "priority": 4,
                "priority_label": "Optional",
                "why_it_matters": f"Nice-to-have for {role['label']} roles, not a blocker.",
                "resource": RESOURCES["default"][0],
                "exercise": RESOURCES["default"][1],
                "project": RESOURCES["default"][2],
                "recommended_proficiency": "Beginner",
            }
        )
    for item in owned_skills:
        if _already_listed(item, rows):
            continue
        rows.append(
            {
                "skill": item,
                "current": "On profile",
                "target": "Your addition",
                "gap": "low",
                "priority": 5,
                "priority_label": "On your profile",
                "why_it_matters": "You added this on your career profile (skill, course, or project tool). It is counted here even if the role catalog does not list it.",
                "resource": RESOURCES["default"][0],
                "exercise": f"Use {item} in a short weekly exercise",
                "project": f"Show {item} in a portfolio note",
                "recommended_proficiency": "Keep using",
            }
        )
    rows.sort(key=lambda r: r["priority"])
    return rows


def _already_listed(item: str, rows: list[dict]) -> bool:
    key = (item or "").strip().lower()
    if not key:
        return True
    for row in rows:
        skill = str(row.get("skill") or "").lower()
        if key == skill or key in skill or skill in key:
            return True
    return False


def _priority_label(gap: str, current: str) -> str:
    if gap == "high":
        return "Focus next"
    if gap == "medium":
        return "Stretch"
    if (current or "").lower() == "missing":
        return "Optional"
    return "On track"


def _explain_gap(skill: str, current: str, target: str, gap: str, role_label: str) -> str:
    if gap == "low":
        return (
            f"On track: you already list {skill} at {current}, which meets the {target} bar for {role_label}. "
            "This column is remaining learning gap, not how weak the skill is."
        )
    if gap == "medium":
        return f"You show some {skill}, but {role_label} typically wants {target}. One step up would close this."
    return f"{skill} is missing or well below the {target} level {role_label} roles usually need."


def fit_breakdown(gaps: list[dict], readiness: float) -> dict[str, Any]:
    required = [g for g in gaps if g.get("target") not in ("Optional", "Your addition")]
    on_track = [g["skill"] for g in required if g.get("gap") == "low"]
    stretch = [g["skill"] for g in required if g.get("gap") == "medium"]
    focus = [g["skill"] for g in required if g.get("gap") == "high"]
    listed = ", ".join(on_track[:6]) if on_track else "none of the required skills yet"
    drop = ", ".join(focus[:6]) if focus else "nothing major"
    return {
        "percent": readiness,
        "required_count": len(required),
        "on_track": on_track,
        "stretch": stretch,
        "focus": focus,
        "formula": (
            f"Fit ({readiness}%) is the average of (your level ÷ the role's required level) "
            f"across {len(required)} required skills. Missing = 0, Beginner = 1, Intermediate = 2, Strong = 3. "
            f"Skills already on your profile ({listed}) raise this number. "
            f"The remaining drop comes from skills still below target ({drop})."
        ),
    }


def _gap(current: str, target: str) -> str:
    diff = LEVEL_RANK.get(target, 2) - LEVEL_RANK.get(current, 0)
    if diff >= 2:
        return "high"
    if diff == 1:
        return "medium"
    return "low"


def readiness_from_gaps(gaps: list[dict]) -> float:
    if not gaps:
        return 0
    required = [g for g in gaps if g.get("target") not in ("Optional", "Your addition")]
    if not required:
        return 0
    score = 0
    for g in required:
        cur = LEVEL_RANK.get(g["current"].lower(), 0)
        tgt = LEVEL_RANK.get(g["target"].lower(), 2)
        score += min(cur / max(tgt, 1), 1)
    return round(100 * score / len(required), 1)


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
DAY_KINDS = (
    ("Learn", "Study one focused lesson on {skill} and write 8 notes."),
    ("Practice", "Do a 45-minute exercise in {skill} and save the output."),
    ("Build", "Produce a real draft or artifact using {skill}."),
    ("Apply", "Use {skill} on a piece you can show someone else."),
    ("Review", "Revise yesterday's work in {skill} and list one gap left."),
)


def skill_focus_rows(skill: str) -> list[dict[str, Any]]:
    name = (skill or "").strip() or "this skill"
    key = name.lower()
    if "research" in key and "writ" in key:
        facets = [
            "Research question and scope",
            "Finding and evaluating sources",
            "Note-taking and evidence",
            "Outline and argument",
            "Drafting the paper",
            "Citation and academic honesty",
            "Revision and peer feedback",
            "Abstract, title, and presentation",
        ]
    elif "writ" in key:
        facets = [
            f"{name} purpose and audience",
            f"{name} structure and outline",
            f"Drafting in {name}",
            f"Clarity and style in {name}",
            f"Editing and proofreading {name}",
            f"Sharing and presenting {name}",
        ]
    else:
        facets = [
            f"{name} fundamentals",
            f"{name} methods and examples",
            f"Planning work in {name}",
            f"Guided practice in {name}",
            f"Independent project in {name}",
            f"Feedback and revision in {name}",
            f"Showcasing {name}",
        ]
    rows = []
    for facet in facets:
        rows.append(
            {
                "skill": facet,
                "parent": name,
                "current": "Learning",
                "target": "Skill focus",
                "gap": "medium",
                "priority": 1,
                "priority_label": "Focus",
                "why_it_matters": f"Part of a plan for {name} only — not other tools from your profile.",
                "resource": f"A reputable guide or course on {name}",
                "exercise": f"A short exercise for {facet.lower()}",
                "project": f"One artifact that proves progress in {name}",
                "recommended_proficiency": "Working",
                "mode": "skill",
            }
        )
    return rows


def resolve_schedule(unit: str, value: int, months_fallback: int = 3) -> list[int]:
    """Return the number of weekdays in each week of the plan."""
    unit = (unit or "months").strip().lower()
    raw = int(value or 0)
    if raw <= 0:
        raw = months_fallback if months_fallback in (1, 3, 6, 12) else 3
        unit = "months"
    if unit in ("day", "days"):
        days = min(max(raw, 1), 120)
    elif unit in ("week", "weeks"):
        days = min(max(raw, 1), 52) * 5
    else:
        months = min(max(raw, 1), 24)
        days = months * 20
    weeks: list[int] = []
    left = days
    while left > 0:
        chunk = min(5, left)
        weeks.append(chunk)
        left -= chunk
    return weeks or [5]


def build_roadmap(
    gaps: list[dict],
    duration_months: int = 3,
    target_role: str = "",
    focus_skill: str = "",
    duration_unit: str = "months",
    duration_value: int | None = None,
) -> list[dict]:
    focus = (focus_skill or "").strip()
    role_name = (target_role or "").strip()
    if focus:
        cycle = skill_focus_rows(focus)
        label = focus
    elif role_name and not is_catalog_role(role_name):
        cycle = skill_focus_rows(role_name)
        label = role_name
    else:
        cycle = [g for g in gaps if g.get("target") not in ("Optional", "Your addition")]
        if not cycle:
            cycle = skill_focus_rows(role_name or "your target role")
        label = get_role(role_name).get("label") if role_name and is_catalog_role(role_name) else (role_name or "this plan")
    value = duration_value if duration_value is not None else duration_months
    week_sizes = resolve_schedule(duration_unit, value, duration_months)
    duration_label = _duration_label(duration_unit, value, duration_months)
    milestones = []
    idx = 0
    for week, n_days in enumerate(week_sizes, start=1):
        month = ((week - 1) // 4) + 1
        tasks = []
        week_skills = []
        for day_i in range(n_days):
            g = cycle[idx % len(cycle)]
            idx += 1
            skill = g.get("skill") or label
            week_skills.append(skill)
            day = WEEKDAYS[day_i]
            kind, prompt = DAY_KINDS[day_i]
            tasks.append(
                {
                    "id": f"w{week}-d{day_i + 1}",
                    "title": f"{day}: {kind} · {skill}",
                    "skill": skill,
                    "day": day,
                    "objective": prompt.format(skill=skill),
                    "priority": g.get("gap") or "medium",
                    "resource": g.get("resource") or f"A reputable guide on {label}",
                    "exercise": g.get("exercise") or DAY_KINDS[1][1].format(skill=skill),
                    "project": g.get("project") or f"One artifact for {label}",
                    "expected_result": f"Progress in {label} — not a different tool from your profile.",
                    "deadline": f"Week {week} · {day}",
                    "completed": False,
                    "kind": "system",
                }
            )
        unique = list(dict.fromkeys(week_skills))
        milestones.append(
            {
                "month": month,
                "week": week,
                "duration_label": duration_label,
                "title": f"Week {week}: {', '.join(unique[:3])}",
                "tasks": tasks,
            }
        )
    return milestones


def _duration_label(unit: str, value: int | None, months_fallback: int) -> str:
    raw = int(value or months_fallback or 1)
    unit = (unit or "months").lower()
    if unit in ("day", "days"):
        return f"{raw} day" if raw == 1 else f"{raw} days"
    if unit in ("week", "weeks"):
        return f"{raw} week" if raw == 1 else f"{raw} weeks"
    return f"{raw} month" if raw == 1 else f"{raw} months"


def compare_roles(owned: list[str], role_a: str, role_b: str) -> dict[str, Any]:
    a, b = get_role(role_a), get_role(role_b)
    ga, gb = analyze_skill_gap(owned, role_a), analyze_skill_gap(owned, role_b)
    ra, rb = readiness_from_gaps(ga), readiness_from_gaps(gb)
    if ra == rb:
        recommendation = (
            f"Neither is a closer fit yet — both sit at {ra}% against your current profile. "
            "Fit is the share of that role's typical requirements that already show up in your skills and work. "
            "Equal low scores usually mean your profile does not yet evidence either craft, not that the two careers are the same."
        )
        closer = None
    elif ra > rb:
        recommendation = (
            f"{a['label']} is a closer fit right now ({ra}% vs {rb}%) because more of its required skills "
            "already appear in your profile."
        )
        closer = a["label"]
    else:
        recommendation = (
            f"{b['label']} is a closer fit right now ({rb}% vs {ra}%) because more of its required skills "
            "already appear in your profile."
        )
        closer = b["label"]
    return {
        "role_a": {"name": a["label"], "description": a["description"], "readiness": ra, "gaps": ga, "source": a.get("source", "catalog")},
        "role_b": {"name": b["label"], "description": b["description"], "readiness": rb, "gaps": gb, "source": b.get("source", "catalog")},
        "closer": closer,
        "recommendation": recommendation,
        "fit_meaning": (
            f"Fit is the average of (your level ÷ required level) across each role's required skills. "
            f"{a['label']}: {ra}% from {len([g for g in ga if g.get('target') not in ('Optional', 'Your addition')])} required skills. "
            f"{b['label']}: {rb}% from {len([g for g in gb if g.get('target') not in ('Optional', 'Your addition')])} required skills. "
            "On track in the table means you already meet that skill — it is not a low rating."
        ),
        "fit_a": fit_breakdown(ga, ra),
        "fit_b": fit_breakdown(gb, rb),
        "disclaimer": "Readiness is an AI-generated estimate for personal tracking, not a hiring guarantee.",
    }


def career_reply(
    message: str,
    profile_text: str,
    memory_text: str,
    rag_context: str,
    advanced: bool = False,
    plan: str = "pro",
    history: list[dict[str, Any]] | None = None,
) -> tuple[str, bool]:
    if not gateway.enabled:
        return (
            _demo_reply(message, profile_text),
            True,
        )
    recent = []
    for turn in (history or [])[-10:]:
        role = str(turn.get("role") or "")
        content = str(turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            recent.append(f"{role}: {content[:800]}")
    messages = [
        {
            "role": "system",
            "content": SAFETY_PREAMBLE
            + "\nYou are the Career Agent. Use the profile only as silent context. "
            "Answer the latest user_message and nothing else. "
            "Match the length of the question: a short reaction gets 1–3 sentences. "
            "Do not dump a Profile Summary, Skills and Gaps list, or full CV unless they explicitly ask. "
            "If they say they did not ask for something, apologize briefly and ask what they want instead. "
            "Coach any career they name. Never invent facts. "
            "If they ask to compare roles, weigh both against their actual background. "
            "Use ## / ### headings only when the answer needs sections. Never use ####.",
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    wrap_untrusted("user_profile", profile_text),
                    wrap_untrusted("career_memory", memory_text or "None"),
                    wrap_untrusted("retrieved_knowledge", rag_context or "None"),
                    wrap_untrusted("recent_chat", "\n".join(recent) if recent else "None"),
                    wrap_untrusted("user_message", message),
                ]
            ),
        },
    ]
    text = gateway.complete(messages, task="deep_career" if advanced else "career", advanced=advanced, plan=plan)
    if not text:
        if gateway.last_error:
            return (
                "I could not reach the language model. "
                f"Technical detail: {gateway.last_error}\n\n"
                "Confirm `LLM_BASE_URL=https://api.openai.com/v1` and `LLM_MODEL=gpt-4o-mini` in `backend/.env`, then restart the backend.",
                False,
            )
        return _demo_reply(message, profile_text), True
    return text, False


def extract_memories(message: str) -> list[dict[str, str]]:
    """Pull lasting preferences from a user message. Empty if nothing durable."""
    if not gateway.enabled or len(message) < 20:
        return []
    data = gateway.complete_json(
        [
            {
                "role": "system",
                "content": SAFETY_PREAMBLE
                + "\nExtract durable career preferences only (direction, learning goals, resume tastes, interview weaknesses, decisions). "
                "Return JSON {memories: [{category, key, value}]} with 0-3 items. "
                "category must be one of: direction, learning, resume, interview, decision. "
                "If the message is a one-off question, return {memories: []}. Never invent facts about the user.",
            },
            {"role": "user", "content": wrap_untrusted("user_message", message)},
        ],
        task="memory",
    )
    items = (data or {}).get("memories") if data else None
    if not isinstance(items, list):
        return []
    out = []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()[:120]
        value = str(item.get("value") or "").strip()[:500]
        category = str(item.get("category") or "direction").strip()[:64]
        if key and value:
            out.append({"category": category, "key": key, "value": value})
    return out


def _demo_reply(message: str, profile_text: str) -> str:
    text = (message or "").strip()
    if len(text) < 24:
        return (
            f"Understood — “{text or 'okay'}”. What should we do next: compare two roles, "
            "check a skill gap, or pick one action for this week?"
        )
    return (
        f"On your question — “{text[:180]}” — I can work from the profile without repeating it.\n\n"
        "Say whether you want a role comparison, a gap on one skill, or a next step for this week, "
        "and I will stay on that."
    )
