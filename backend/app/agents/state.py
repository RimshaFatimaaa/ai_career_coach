from typing import Any, Literal, Optional, TypedDict


class CoachState(TypedDict, total=False):
    user_id: int
    intent: Literal["career", "skill_gap", "roadmap", "resume", "ats", "interview", "chat"]
    message: str
    profile_text: str
    memory_text: str
    rag_context: str
    target_role: str
    compare_role: str
    duration_months: int
    job_description: str
    allowed_facts: dict[str, Any]
    result: dict[str, Any]
    reply: str
    demo: bool
    plan: str
    advanced: bool
    history: list[dict[str, Any]]
