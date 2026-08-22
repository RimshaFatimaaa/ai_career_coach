# MCP integrations

Atelier exposes career tools over HTTP JSON-RPC at `POST /mcp`, authenticated with the same Bearer token as the rest of the API.

Supported methods: `initialize`, `tools/list`, `tools/call`.

Tools: `get_dashboard`, `get_profile_summary`, `analyze_skill_gap`, `list_resumes`, `list_reminders`, `career_analytics`.

This is the product MCP surface. It does not grant access to other users' data, and it does not scrape third-party sites.
