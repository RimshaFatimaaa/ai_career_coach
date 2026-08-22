"""LangGraph supervisor: route a request to career / resume / interview workflows."""

from __future__ import annotations

from typing import Any, Literal

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - Python 3.14 / missing extra
    END = START = StateGraph = None  # type: ignore

from app.agents.career import career_reply
from app.agents.state import CoachState

Intent = Literal["career", "skill_gap", "roadmap", "resume", "interview", "chat"]


def classify_intent(message: str) -> Intent:
    m = message.lower()
    if any(w in m for w in ("skill gap", "skill-gap", "missing skills", "readiness")):
        return "skill_gap"
    if any(w in m for w in ("roadmap", "learning plan", "study plan", "milestones")):
        return "roadmap"
    if any(w in m for w in ("resume", "cv", "ats", "cover letter", "tailor")):
        return "resume"
    if any(w in m for w in ("interview", "mock", "behavioral", "star")):
        return "interview"
    return "career"


def supervisor_node(state: CoachState) -> dict[str, Any]:
    intent = state.get("intent") or classify_intent(state.get("message") or "")
    return {"intent": intent}


def career_node(state: CoachState) -> dict[str, Any]:
    reply, demo = career_reply(
        state.get("message") or "",
        state.get("profile_text") or "",
        state.get("memory_text") or "",
        state.get("rag_context") or "",
        advanced=bool(state.get("advanced")),
        plan=state.get("plan") or "free",
        history=state.get("history") or [],
    )
    return {"reply": reply, "demo": demo, "result": {"kind": "career_chat"}}


def route_after_supervisor(state: CoachState) -> str:
    intent = state.get("intent") or "career"
    if intent in ("resume", "interview", "skill_gap", "roadmap"):
        return intent
    return "career"


def build_supervisor_graph():
    if StateGraph is None:
        raise RuntimeError("langgraph is not installed")
    graph = StateGraph(CoachState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("career", career_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "career": "career",
            "skill_gap": "career",
            "roadmap": "career",
            "resume": "career",
            "interview": "career",
        },
    )
    graph.add_edge("career", END)
    return graph.compile()


def run_career_chat(payload: CoachState) -> CoachState:
    """Entry used by the API. Dedicated endpoints handle skill-gap, resume, interview loops."""
    if not payload.get("intent"):
        payload["intent"] = classify_intent(payload.get("message") or "")
    try:
        graph = build_supervisor_graph()
        return graph.invoke(payload)
    except Exception:
        reply, demo = career_reply(
            payload.get("message") or "",
            payload.get("profile_text") or "",
            payload.get("memory_text") or "",
            payload.get("rag_context") or "",
            advanced=bool(payload.get("advanced")),
            plan=payload.get("plan") or "free",
            history=payload.get("history") or [],
        )
        return {**payload, "reply": reply, "demo": demo}


supervisor_graph = None

