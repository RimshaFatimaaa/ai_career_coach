"""HTTP MCP-style tool server (PRD Phase 3). Same auth as the rest of the API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.career import analyze_skill_gap, readiness_from_gaps
from app.deps import CurrentUser, DbDep
from app.models import Resume
from app.services.analytics import analytics_payload
from app.services.billing import assert_within_limit, consume
from app.services.catalog import collect_profile_skills
from app.services.profile import dashboard_payload, ensure_profile, profile_to_text
from app.services.reminders import list_reminders

router = APIRouter(tags=["mcp"])


TOOLS = [
    {
        "name": "get_dashboard",
        "description": "Readiness, resume health, interview performance, and next action.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_profile_summary",
        "description": "Plain-text career profile the coach uses as source of truth.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "analyze_skill_gap",
        "description": "Skill-gap table for a target role using the saved profile.",
        "input_schema": {
            "type": "object",
            "properties": {"target_role": {"type": "string"}},
            "required": ["target_role"],
        },
    },
    {
        "name": "list_resumes",
        "description": "Active resumes with titles and templates.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_reminders",
        "description": "Open personalized reminders.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "career_analytics",
        "description": "Interview trends, ATS history, skill-gap mix.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class RpcIn(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str = 1
    method: str
    params: dict[str, Any] = {}


def _run_tool(name: str, arguments: dict, user, db) -> Any:
    if name == "get_dashboard":
        return dashboard_payload(db, user)
    if name == "get_profile_summary":
        profile = ensure_profile(db, user)
        return {"text": profile_to_text(user, profile)}
    if name == "analyze_skill_gap":
        role = (arguments or {}).get("target_role") or ""
        if not role:
            raise HTTPException(400, "target_role is required")
        assert_within_limit(db, user, "skill_gap_analyses")
        consume(db, user, "skill_gap_analyses")
        profile = ensure_profile(db, user)
        gaps = analyze_skill_gap(collect_profile_skills(profile), role, plan=user.plan)
        return {"target_role": role, "readiness": readiness_from_gaps(gaps), "gaps": gaps[:12]}
    if name == "list_resumes":
        rows = db.query(Resume).filter_by(user_id=user.id, is_active=True).all()
        return [{"id": r.id, "title": r.title, "template": r.template, "target_role": r.target_role} for r in rows]
    if name == "list_reminders":
        return list_reminders(db, user)
    if name == "career_analytics":
        return analytics_payload(db, user)
    raise HTTPException(404, f"Unknown tool: {name}")


# JSON-RPC 2.0 reserved codes. MCP clients parse these; an HTTP error body
# from FastAPI is not something they can interpret.
INVALID_PARAMS = -32602
METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603


def _rpc_error(rpc_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


@router.get("/api/mcp/tools")
def list_tools(_: CurrentUser):
    return {"tools": TOOLS, "note": "Call POST /mcp with JSON-RPC tools/list or tools/call. Authenticate with the same Bearer token."}


@router.post("/mcp")
def mcp_rpc(payload: RpcIn, user: CurrentUser, db: DbDep):
    if payload.method == "tools/list":
        return {"jsonrpc": "2.0", "id": payload.id, "result": {"tools": TOOLS}}
    if payload.method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": payload.id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "atelier-career-coach", "version": "0.3.0"},
                "capabilities": {"tools": {}},
            },
        }
    if payload.method == "tools/call":
        name = payload.params.get("name")
        arguments = payload.params.get("arguments") or payload.params.get("args") or {}
        if not name:
            return _rpc_error(payload.id, INVALID_PARAMS, "params.name is required")
        try:
            result = _run_tool(name, arguments, user, db)
        except HTTPException as exc:
            code = METHOD_NOT_FOUND if exc.status_code == 404 else INVALID_PARAMS
            return _rpc_error(payload.id, code, str(exc.detail))
        except Exception:
            return _rpc_error(payload.id, INTERNAL_ERROR, f"Tool {name} failed")
        return {"jsonrpc": "2.0", "id": payload.id, "result": {"content": [{"type": "json", "json": result}]}}
    return _rpc_error(payload.id, METHOD_NOT_FOUND, f"Unsupported method {payload.method}")
