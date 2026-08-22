"""Adaptive mock-interview loop and STAR / technical evaluation."""

from __future__ import annotations

import random
import re
import secrets
from typing import Any

from app.services.catalog import get_role, normalize_role
from app.services.llm import SAFETY_PREAMBLE, gateway, wrap_untrusted
from app.services.voice import aggregate_voice

WORD_SCORES = {
    "excellent": 90,
    "strong": 82,
    "good": 75,
    "fair": 62,
    "average": 58,
    "okay": 58,
    "ok": 55,
    "weak": 42,
    "poor": 30,
    "missing": 20,
}


def as_score(value: Any, default: float = 0.0, *, scale_unit: bool = False) -> float:
    """Coerce model output to a 0–100 score. Does not treat 0.6 as 60 unless scale_unit=True."""
    if value is None or value is False:
        return float(default)
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        n = float(value)
        if scale_unit and 0 <= n <= 1.5:
            return round(n * 100, 1)
        return n
    if isinstance(value, dict):
        return as_score(value.get("overall") or value.get("score") or value.get("value"), default, scale_unit=scale_unit)
    text = str(value).strip().replace("%", "")
    if not text:
        return float(default)
    key = text.lower()
    if key in WORD_SCORES:
        return float(WORD_SCORES[key])
    try:
        n = float(text.split()[0])
        if scale_unit and 0 <= n <= 1.5:
            return round(n * 100, 1)
        return n
    except ValueError:
        return float(default)


def _looks_unit_scale(values: list[float]) -> bool:
    nums = [v for v in values if v is not None]
    return bool(nums) and max(nums) <= 1.5 and min(nums) >= 0


def _pull_overall(data: dict[str, Any], default: float) -> float:
    nested = data.get("evaluation") if isinstance(data.get("evaluation"), dict) else {}
    scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    candidates = [
        data.get("overall"),
        data.get("score"),
        nested.get("overall") if nested else None,
        scores.get("overall"),
    ]
    raw_nums: list[float] = []
    for src in (scores, data.get("communication") if isinstance(data.get("communication"), dict) else {}):
        for v in src.values():
            try:
                raw_nums.append(float(v))
            except (TypeError, ValueError):
                pass
    scale = _looks_unit_scale(raw_nums)
    for c in candidates:
        if c is None or c == "":
            continue
        return as_score(c, default, scale_unit=scale)
    if scores:
        parts = [as_score(v, default, scale_unit=scale) for v in scores.values()]
        if parts:
            return round(sum(parts) / len(parts), 1)
    return float(default)


def merge_evaluation(llm: dict[str, Any] | None, heuristic: dict[str, Any], answer: str) -> dict[str, Any]:
    """Keep LLM nuance but do not let it park every answer at ~60."""
    h = heuristic
    words = len((answer or "").split())
    if not llm:
        out = dict(h)
        if words < 15:
            out["overall"] = min(as_score(out.get("overall"), 30), 38)
        return out
    scores = llm.get("scores") if isinstance(llm.get("scores"), dict) else {}
    scale = _looks_unit_scale(
        [float(v) for v in scores.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    )
    if scores:
        llm["scores"] = {k: as_score(v, h["overall"], scale_unit=scale) for k, v in scores.items()}
    comm = llm.get("communication")
    if isinstance(comm, dict):
        llm["communication"] = {k: as_score(v, 70, scale_unit=scale) for k, v in comm.items()}
    llm_overall = _pull_overall(llm, h["overall"])
    h_overall = as_score(h.get("overall"), 50)
    if 55 <= llm_overall <= 65 and abs(llm_overall - h_overall) >= 8:
        overall = round(0.2 * llm_overall + 0.8 * h_overall, 1)
    else:
        overall = round(0.55 * llm_overall + 0.45 * h_overall, 1)
    if words < 12:
        overall = min(overall, 28)
    elif words < 25:
        overall = min(overall, 48)
    elif words >= 80 and h_overall >= 70:
        overall = max(overall, min(92, h_overall))
    overall = max(8, min(96, overall))
    llm["overall"] = overall
    if isinstance(llm.get("scores"), dict):
        llm["scores"]["overall"] = overall
    llm.setdefault("strengths", h.get("strengths") or [])
    llm.setdefault("weaknesses", h.get("weaknesses") or [])
    llm.setdefault("improved_example", h.get("improved_example"))
    llm.setdefault("needs_followup", h.get("needs_followup"))
    llm.setdefault("followup_question", h.get("followup_question"))
    llm.setdefault("communication", h.get("communication"))
    return llm

BEHAVIORAL_BANK = [
    "Tell me about a difficult situation you handled recently.",
    "Describe a conflict on a team and how you resolved it.",
    "Tell me about a time you failed. What did you change afterward?",
    "Why should we hire you for this role?",
    "Walk me through a project you are proud of. What was your role?",
    "Describe a time you had to learn something quickly under pressure.",
    "Tell me about a time you disagreed with feedback.",
    "How do you prioritize when everything feels urgent?",
    "Tell me about a time you influenced someone without having authority.",
    "Describe a decision you made with incomplete information.",
    "When did you last change your mind after new evidence?",
    "Tell me about a time you missed a deadline. What happened next?",
    "How do you handle a teammate who is not delivering?",
    "Describe a time you had to say no to a request.",
    "What is the most useful criticism you have received?",
    "Tell me about a time you owned a mistake in public.",
    "How do you start when a brief is vague?",
    "Describe a time you balanced quality against a hard deadline.",
    "Tell me about someone you helped grow, and how you knew it worked.",
    "What would your last collaborator say you should improve?",
]

TECHNICAL_BANK = {
    "ai engineer": [
        "How would you design a RAG pipeline for an internal knowledge base?",
        "What is the difference between fine-tuning and prompt engineering? When would you choose each?",
        "How do you evaluate an LLM application beyond 'it looks good'?",
        "Explain embeddings and why chunking strategy matters.",
        "How would you keep a resume-tailoring agent from inventing facts?",
        "Walk through how you would productionize a FastAPI + LangGraph service.",
        "How would you reduce hallucinations in a customer-facing chatbot?",
        "What would you log and monitor after shipping an LLM feature?",
        "How do you choose a model when cost, latency, and quality all matter?",
        "Describe how you would test a prompt change without breaking older flows.",
    ],
    "data scientist": [
        "How do you decide between a simple baseline and a complex model?",
        "Explain train/validation/test leakage with an example.",
        "How would you measure whether a new feature improved a model?",
        "SQL: how would you find the second-highest salary per department?",
        "How do you communicate uncertainty to a non-technical stakeholder?",
        "A metric jumped after a dashboard refresh. How do you investigate?",
        "How would you design an A/B test for a ranking change?",
        "What do you do when stakeholders want a model that the data cannot support?",
        "How would you handle missing labels in a classification problem?",
    ],
    "software engineer": [
        "Explain the difference between processes and threads.",
        "How would you design a URL shortener?",
        "What is the time complexity of searching vs hashing?",
        "How do you test an API that depends on an external service?",
        "Describe a bug you tracked down. What was the root cause?",
        "How would you make a slow endpoint faster without rewriting everything?",
        "Walk through how you would roll back a bad deploy.",
        "How do you decide what belongs in a database vs the application layer?",
        "What would you check first if a service is healthy but users still see errors?",
    ],
    "default": [
        "Explain a technical concept from your resume as if I am a hiring manager.",
        "How do you debug a system you did not write?",
        "What tradeoffs did you make on your most recent project?",
        "How do you decide what to build first when the list is too long?",
        "Walk me through how you would review someone else's work in this field.",
        "What would you measure to know a process or tool is actually helping?",
        "Describe a time a tool or method failed you. What did you switch to?",
    ],
}


ROLE_CRAFT_BANK = {
    "architect": [
        "Walk me through a studio or built project from brief to drawings. What was your design intent?",
        "How did site analysis change the plan or massing on a recent project?",
        "Tell me about a building code, accessibility, or structure constraint that forced a redesign.",
        "How do you move between sketch, CAD or Revit, and a physical or digital model?",
        "Describe a crit that made you redo a plan, section, or elevation. What did you change?",
        "How would you explain a concept to a client who does not read drawings?",
        "Talk about daylight, circulation, or material choice on a project you care about.",
        "How do you coordinate with structure or MEP as a student or junior designer?",
        "Walk through a construction detail or drawing set you are proud of.",
        "How do you balance program, context, and budget on a tight site?",
        "What would you put first in an architecture portfolio, and why that project?",
        "Tell me about a time the existing building or site fought the scheme you wanted.",
    ],
    "interior designer": [
        "Walk me through an interior from brief to finishes. What drove the spatial idea?",
        "How do you choose materials and furniture against a real budget?",
        "Tell me about a client who wanted a look that would not work in the space.",
        "How do you handle lighting, circulation, and storage in a compact interior?",
        "Describe a detailing or joinery problem you had to solve.",
    ],
    "artist": [
        "Walk me through a work in your portfolio: intent, process, and what you would change.",
        "How do you take studio critique without losing the piece?",
        "Tell me about a material or medium constraint that shaped the work.",
        "How do you know a piece is finished enough to show?",
        "What does your artist statement leave out that an interviewer should still hear?",
    ],
    "graphic designer": [
        "Walk me through a identity or layout project from brief to final files.",
        "How do you defend a typographic or hierarchy choice to a client?",
        "Tell me about a constraint that improved the design.",
        "How do you work with developers or printers without losing the design?",
    ],
    "nurse": [
        "Walk me through a shift where priorities changed suddenly. What did you do first?",
        "How do you communicate with a patient or family under stress?",
        "Tell me about a protocol or safety check you refused to skip.",
        "Describe working with a multidisciplinary team on a difficult case.",
    ],
    "teacher": [
        "Walk me through a lesson that did not land. What did you change the next day?",
        "How do you handle mixed ability in one classroom?",
        "Tell me about communicating with a parent or guardian about a concern.",
        "How do you know students actually learned, not just finished the activity?",
    ],
}


COMPUTING_LEAK = re.compile(
    r"\b(python|langchain|langgraph|fastapi|pytorch|tensorflow|llm|gpt-?\d|chatgpt|"
    r"rag pipeline|retrieval.augmented|embedding|vector store|fine-?tun|"
    r"prompt engineer|hallucinat|neural network|machine learning|deep learning|"
    r"kubernetes|docker compose|microservice|rest api|graphql|javascript|typescript|"
    r"react native|next\.js|software engineer|leetcode|binary tree|hash map)\b",
    re.I,
)


CRAFT_BANK = [
    "Walk me through a piece of work from your portfolio. What was the brief, and what did you personally do?",
    "Tell me about a project that did not go as planned. What did you change?",
    "How do you take critique and decide what to revise?",
    "Why this role, and why now?",
    "Describe how you work with clients, patients, students, or collaborators in this field.",
    "What does a strong day of practice look like for you?",
    "Tell me about a constraint (budget, time, materials, policy) that shaped the work.",
    "How do you know when a piece of work is finished enough to share?",
    "What part of this craft do you still find hardest, and how are you practicing it?",
    "Walk me through how you research before you start making.",
    "Tell me about a time your taste and a client's taste did not match.",
    "How do you document or present work so someone else can understand the choices?",
    "Describe a piece you would not put in a portfolio, and why.",
    "What standards do you refuse to drop even when time is short?",
    "How do you stay current in this field without copying other people's work?",
    "Tell me about a collaboration where your role was not the lead.",
]


VARIATION_ANGLES = [
    "recent work and collaboration",
    "judgment under constraints",
    "learning, mistakes, and growth",
    "stakeholder or client communication",
    "quality standards and taste",
    "priorities and tradeoffs",
    "ownership when things go wrong",
    "starting from an unclear brief",
]


def _norm_prompt(prompt: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (prompt or "").lower()).strip()


COMPUTING_HINTS = (
    "software engineer",
    "ai engineer",
    "data scientist",
    "data analyst",
    "machine learning",
    "developer",
    "programmer",
    "devops",
    "backend",
    "frontend",
    "full stack",
    "sre",
    "ml engineer",
    "llm",
)


def _is_computing_role(target_role: str) -> bool:
    key = normalize_role(target_role)
    return any(h in key for h in COMPUTING_HINTS)


def _craft_prompts_for(target_role: str, computing: bool) -> list[str]:
    key = normalize_role(target_role)
    if computing:
        return TECHNICAL_BANK.get(key) or TECHNICAL_BANK.get("default") or []
    return list(ROLE_CRAFT_BANK.get(key) or []) + list(CRAFT_BANK)


def _prompt_fits_role(prompt: str, computing: bool) -> bool:
    if computing:
        return True
    return not COMPUTING_LEAK.search(prompt or "")


def _stamp(questions: list[dict], count: int) -> list[dict]:
    out = []
    for i, q in enumerate(questions[:count]):
        item = dict(q)
        item["index"] = i
        item["session_total"] = count
        item.setdefault("is_followup", False)
        item.setdefault("answer", None)
        item.setdefault("evaluation", None)
        out.append(item)
    return out


def _pad_to_count(
    out: list[dict],
    pool: list[tuple[str, str]],
    count: int,
    avoid: set[str] | None = None,
) -> list[dict]:
    fallback = list(pool or [("behavioral", "Walk me through a recent piece of work and your role in it.")])
    rng = random.Random(secrets.randbits(64))
    rng.shuffle(fallback)
    blocked = avoid or set()
    seen = {_norm_prompt(str(q.get("prompt") or "")) for q in out}
    unused = [(k, p) for k, p in fallback if _norm_prompt(p) not in seen and _norm_prompt(p) not in blocked]
    reuse = [(k, p) for k, p in fallback if _norm_prompt(p) not in seen]
    i = 0
    queue = unused + reuse
    while len(out) < count and queue:
        kind, prompt = queue[i % len(queue)]
        i += 1
        key = _norm_prompt(prompt)
        if key in seen:
            if i > len(queue) * 2:
                break
            continue
        seen.add(key)
        out.append(
            {
                "index": len(out),
                "type": kind,
                "prompt": prompt,
                "is_followup": False,
                "answer": None,
                "evaluation": None,
            }
        )
    return _stamp(out, count)


def _shuffled_pool(
    interview_type: str,
    computing: bool,
    role_bank: list[str],
    avoid: set[str],
) -> list[tuple[str, str]]:
    rng = random.Random(secrets.randbits(64))
    craft_type = "technical" if computing else "craft"
    behavioral = [("behavioral", q) for q in BEHAVIORAL_BANK]
    role = [(craft_type, q) for q in role_bank]
    rng.shuffle(behavioral)
    rng.shuffle(role)
    if interview_type == "behavioral":
        raw = behavioral
    elif interview_type == "technical":
        raw = role or behavioral
    else:
        raw = []
        for i in range(max(len(behavioral), len(role))):
            if i < len(behavioral):
                raw.append(behavioral[i])
            if i < len(role):
                raw.append(role[i])
    fresh = [item for item in raw if _norm_prompt(item[1]) not in avoid]
    used = [item for item in raw if _norm_prompt(item[1]) in avoid]
    return fresh + used


def plan_questions(
    target_role: str,
    interview_type: str,
    count: int,
    profile_text: str,
    job_description: str,
    avoid_prompts: list[str] | None = None,
) -> list[dict]:
    count = max(3, min(int(count or 6), 12))
    computing = _is_computing_role(target_role)
    role_bank = _craft_prompts_for(target_role, computing)
    spec = get_role(target_role)
    role_label = spec.get("label") or target_role
    skills = ", ".join(list((spec.get("required") or {}).keys())[:8])
    avoid = {_norm_prompt(p) for p in (avoid_prompts or []) if p}
    pool = _shuffled_pool(interview_type, computing, role_bank, avoid)
    pool = [(k, p) for k, p in pool if _prompt_fits_role(p, computing)] or pool
    angle = VARIATION_ANGLES[secrets.randbelow(len(VARIATION_ANGLES))]
    token = secrets.token_hex(3)
    if gateway.enabled:
        recent = [p for p in (avoid_prompts or []) if p][:18]
        field_rule = (
            f"This interview is ONLY for {role_label} ({target_role}). "
            f"Domain: {spec.get('description') or role_label}. Typical craft: {skills or 'this field'}. "
            "Every question must be one a hiring panel in that field would actually ask. "
            "The candidate profile may mention another field of study — ignore that for topic choice. "
            "Do not ask about Python, LLMs, machine learning, software engineering, or coding "
            f"unless the TARGET ROLE itself is computing. Target role: {target_role}."
            if not computing
            else f"Target role is computing: {target_role}. Technical questions should match that stack."
        )
        messages = [
            {
                "role": "system",
                "content": SAFETY_PREAMBLE
                + "\nYou are the Interview Agent planner. Return JSON {questions: [{type, prompt}]} "
                f"with exactly {count} original questions and no more. Session token: {token}. "
                f"Variation angle for this session: {angle}. "
                "Write a fresh set — different topics and wording from a typical first-round script. "
                "Do not reuse questions from the avoid list. "
                f"Types: behavioral, or {'technical' if computing else 'craft/domain'}. {field_rule} "
                "Do not ask about protected characteristics.",
            },
            {
                "role": "user",
                "content": "\n\n".join(
                    [
                        wrap_untrusted("profile", profile_text),
                        wrap_untrusted("job_description", job_description or "None"),
                        wrap_untrusted("avoid_recent_questions", "\n".join(recent) or "None"),
                        f"Interview role (authoritative): {role_label}. Type: {interview_type}. Count: {count}. Angle: {angle}.",
                    ]
                ),
            },
        ]
        data = gateway.complete_json(messages, task="interview")
        if data and isinstance(data.get("questions"), list) and data["questions"]:
            out = []
            seen = set()
            for i, q in enumerate(data["questions"][:count]):
                prompt = q.get("prompt") or q.get("question")
                if not prompt or not _prompt_fits_role(prompt, computing):
                    continue
                key = _norm_prompt(prompt)
                if key in seen or key in avoid:
                    continue
                seen.add(key)
                out.append(
                    {
                        "index": i,
                        "type": q.get("type") or interview_type,
                        "prompt": prompt,
                        "is_followup": False,
                        "answer": None,
                        "evaluation": None,
                    }
                )
            if out:
                return _pad_to_count(out, pool, count, avoid)
    out = []
    for kind, prompt in pool:
        if len(out) >= count:
            break
        out.append(
            {
                "index": len(out),
                "type": kind,
                "prompt": prompt,
                "is_followup": False,
                "answer": None,
                "evaluation": None,
            }
        )
    return _pad_to_count(out, pool, count, avoid)


def apply_followup(qs: list[dict], current_index: int, evaluation: dict) -> list[dict]:
    """Replace the next unanswered question. Never grow the planned list."""
    planned = int((qs[0].get("session_total") if qs else 0) or len(qs))
    qs = [dict(q) for q in qs[:planned]]
    follow = evaluation.get("needs_followup") and evaluation.get("followup_question")
    current = qs[current_index] if 0 <= current_index < len(qs) else {}
    if follow and not current.get("is_followup") and current_index + 1 < len(qs):
        nxt = dict(qs[current_index + 1])
        if not nxt.get("answer"):
            nxt["prompt"] = evaluation["followup_question"]
            nxt["is_followup"] = True
            nxt["type"] = current.get("type")
            nxt["session_total"] = planned
            qs[current_index + 1] = nxt
    return qs


def evaluate_answer(question: dict, answer: str, profile_text: str, advanced: bool = False, plan: str = "pro") -> dict[str, Any]:
    qtype = question.get("type") or "behavioral"
    baseline = heuristic_eval(qtype, answer)
    if not gateway.enabled:
        return baseline
    rubric = (
        "Score each field as a number from 0 to 100 (never 0–1, never a word like Fair). "
        "Fields: situation, task, action, result, relevance, clarity, specificity, overall."
        if qtype == "behavioral"
        else "Score each field as a number from 0 to 100 (never 0–1, never a word). "
        "Fields: correctness, conceptual_understanding, reasoning, practical_knowledge, completeness, relevance, overall."
    )
    messages = [
        {
            "role": "system",
            "content": SAFETY_PREAMBLE
            + "\nYou are the Evaluation Agent. "
            + rubric
            + " overall MUST be a number 0–100 and MUST vary with answer quality. "
            "Vague, one-line, or 'I don't know' answers score 15–35. "
            "Thin answers without an example score 35–50. "
            "Specific STAR answers with actions and results score 75–90. "
            "Do not cluster scores around 60. Do not give every answer the same overall. "
            "Return JSON: scores (object of numbers), overall (number), strengths (list), "
            "weaknesses (list), improved_example (string), needs_followup (bool), "
            "followup_question (string|null), communication (clarity, structure, conciseness as numbers 0–100). "
            "Set needs_followup true only if the answer is too thin to score "
            "(roughly under 40 words or no concrete example). Follow-ups replace a later planned "
            "question; they must not add extra questions beyond the planned set.",
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    wrap_untrusted("profile", profile_text),
                    wrap_untrusted("question", str(question.get("prompt"))),
                    wrap_untrusted("answer", answer),
                    f"Question type: {qtype}. Word count: {len((answer or '').split())}.",
                ]
            ),
        },
    ]
    data = gateway.complete_json(messages, task="evaluate", advanced=advanced, plan=plan)
    return merge_evaluation(data, baseline, answer)


def heuristic_eval(qtype: str, answer: str) -> dict[str, Any]:
    text = (answer or "").strip()
    words = text.split()
    length = len(words)
    has_star = sum(1 for k in ("situation", "task", "action", "result", "i ", "we ") if k in text.lower())
    specificity = 70 if any(ch.isdigit() for ch in text) else 50
    if length < 8:
        overall = 18
        needs = True
        follow = "Can you add a concrete example — what you did and what changed as a result?"
        weaknesses = ["Too short", "Missing a concrete example"]
    elif length < 20:
        overall = 32
        needs = True
        follow = "Can you add a concrete example — what you did and what changed as a result?"
        weaknesses = ["Too short", "Missing a concrete example"]
    elif length > 420:
        overall = 62
        needs = True
        follow = "That was broad. What was the single most important action you took?"
        weaknesses = ["Overlong", "Could be more structured"]
    else:
        overall = min(88, 48 + min(length, 180) / 6 + has_star * 4 + (8 if specificity > 55 else 0))
        needs = overall < 60
        follow = "What was the measurable result?" if needs else None
        weaknesses = [] if overall >= 70 else ["Could quantify the result", "Tighten the structure"]
    strengths = []
    if length >= 40:
        strengths.append("Enough detail to evaluate")
    if has_star >= 2:
        strengths.append("Touches multiple STAR elements")
    scores = {
        "situation": overall - 4,
        "task": overall - 6,
        "action": overall,
        "result": specificity,
        "relevance": overall,
        "clarity": 72 if 40 <= length <= 280 else 58,
        "specificity": specificity,
        "correctness": overall,
        "conceptual_understanding": overall - 2,
        "reasoning": overall - 3,
        "practical_knowledge": overall,
        "completeness": min(90, length / 2),
        "overall": round(overall, 1),
    }
    return {
        "scores": scores,
        "overall": round(overall, 1),
        "strengths": strengths or ["Attempted the question"],
        "weaknesses": weaknesses or ["Add a clearer result"],
        "improved_example": "Use STAR: situation in one sentence, your task, two concrete actions, and a quantified result.",
        "needs_followup": needs,
        "followup_question": follow,
        "communication": {
            "clarity": scores["clarity"],
            "structure": 60 if qtype == "behavioral" and has_star < 2 else 74,
            "conciseness": 55 if length > 350 else 78,
        },
    }


def build_report(questions: list[dict], target_role: str) -> dict[str, Any]:
    evals = [q.get("evaluation") or {} for q in questions if q.get("answer")]
    if not evals:
        return {"overall": 0, "message": "No answers recorded."}
    overall = sum(as_score(e.get("overall"), 0) for e in evals) / len(evals)
    paired = list(zip(questions, [q.get("evaluation") for q in questions]))
    tech = [e for q, e in paired if q.get("type") in ("technical", "craft") and e]
    beh = [e for q, e in paired if q.get("type") == "behavioral" and e]

    def avg_key(items, key, default=70):
        vals = []
        for e in items:
            scores = e.get("scores") or {}
            if key in scores:
                vals.append(as_score(scores[key], default))
            elif key in (e.get("communication") or {}):
                vals.append(as_score(e["communication"][key], default))
            elif key in e:
                vals.append(as_score(e[key], default))
        return round(sum(vals) / len(vals), 1) if vals else default

    strengths = []
    weaknesses = []
    for e in evals:
        strengths.extend(e.get("strengths") or [])
        weaknesses.extend(e.get("weaknesses") or [])
    report = {
        "overall": round(overall, 1),
        "technical_knowledge": round(sum(as_score(e.get("overall"), 0) for e in tech) / len(tech), 1) if tech else None,
        "behavioral": round(sum(as_score(e.get("overall"), 0) for e in beh) / len(beh), 1) if beh else None,
        "communication": avg_key(evals, "clarity"),
        "answer_structure": avg_key(evals, "structure"),
        "relevance": avg_key(evals, "relevance"),
        "strengths": list(dict.fromkeys(strengths))[:6],
        "weaknesses": list(dict.fromkeys(weaknesses))[:6],
        "recommended_practice": [
            "Use STAR for behavioral answers (Situation, Task, Action, Result).",
            "Quantify results where the facts exist — never invent metrics.",
            f"Rehearse {target_role} fundamentals that showed up as weak.",
        ],
        "disclaimer": "Interview scores are AI-generated estimates for coaching, not a hiring decision.",
    }
    voice = aggregate_voice(questions)
    if voice:
        report["voice"] = voice
        report["recommended_practice"] = list(report["recommended_practice"]) + [
            f"Speaking pace was {voice.get('speaking_pace')}. Aim for a steady 120–160 words per minute.",
            "Cut filler words (um, uh, like) — pause instead.",
            f"Average answer length was {voice.get('avg_word_count')} words. Aim for a complete STAR answer, not a one-liner.",
        ]
    return report
