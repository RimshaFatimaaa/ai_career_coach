"""Public GitHub fetch + LinkedIn pasted-text analysis. Never invent employers."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.services.llm import SAFETY_PREAMBLE, gateway, wrap_untrusted


def github_handle(value: str) -> str:
    text = (value or "").strip().rstrip("/")
    text = re.sub(r"^https?://(www\.)?github\.com/", "", text, flags=re.I)
    return text.split("/")[0].lstrip("@")


def fetch_github(handle: str) -> dict[str, Any]:
    user_name = github_handle(handle)
    if not user_name or not re.match(r"^[A-Za-z0-9-]+$", user_name):
        raise ValueError("Enter a GitHub username or profile URL.")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "atelier-career-coach"}
    with httpx.Client(timeout=20.0, headers=headers) as client:
        user_res = client.get(f"https://api.github.com/users/{user_name}")
        if user_res.status_code == 404:
            raise ValueError("GitHub user not found.")
        user_res.raise_for_status()
        user = user_res.json()
        repos_res = client.get(
            f"https://api.github.com/users/{user_name}/repos",
            params={"sort": "updated", "per_page": 12, "type": "owner"},
        )
        if repos_res.status_code == 403:
            # Almost always the unauthenticated hourly rate limit. Falling
            # through would produce an import that looks fine but is built on
            # zero repositories.
            raise RuntimeError("GitHub is rate limiting this server. Try again in a few minutes.")
        repos_res.raise_for_status()
        repos_payload = repos_res.json()
        if not isinstance(repos_payload, list):
            raise RuntimeError("GitHub returned an unexpected response for that account.")
        repos = repos_payload
    public_repos = []
    languages: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        public_repos.append(
            {
                "name": repo.get("name"),
                "description": repo.get("description") or "",
                "language": lang or "",
                "stars": repo.get("stargazers_count") or 0,
                "url": repo.get("html_url"),
                "topics": repo.get("topics") or [],
            }
        )
    ranked = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "source": "github",
        "handle": user_name,
        "name": user.get("name") or user_name,
        "bio": user.get("bio") or "",
        "company": user.get("company") or "",
        "location": user.get("location") or "",
        "blog": user.get("blog") or "",
        "public_repos": user.get("public_repos") or 0,
        "followers": user.get("followers") or 0,
        "languages": [k for k, _ in ranked],
        "repos": public_repos[:8],
        "disclaimer": "Pulled from the public GitHub API. This is not employment history.",
    }


def analyze_import(kind: str, payload: dict[str, Any], profile_text: str, plan: str = "free") -> dict[str, Any]:
    fallback = {
        "summary": payload.get("bio") or "Public profile captured for review.",
        "suggested_skills": payload.get("languages") or [],
        "suggested_projects": [
            {"name": r.get("name"), "description": r.get("description"), "url": r.get("url")}
            for r in (payload.get("repos") or [])[:5]
            if r.get("name")
        ],
        "suggested_experience": [],
        "gaps_vs_profile": [],
        "notes": [
            "Review every suggestion before adding it to your career profile.",
            "GitHub activity is not a job. LinkedIn paste is only as accurate as the text you provided.",
        ],
        "disclaimer": "Suggestions are extracted from public or pasted text, not invented employers.",
    }
    if not gateway.enabled:
        return fallback
    messages = [
        {
            "role": "system",
            "content": SAFETY_PREAMBLE
            + "\nYou extract career facts from a public/pasted profile. "
            "Return JSON: summary, suggested_skills (list of strings), "
            "suggested_projects ([{name, description}]), suggested_experience ([{title, company, notes}]), "
            "gaps_vs_profile (list of strings), notes (list). "
            "Do not invent companies, titles, degrees, or metrics that are not in the source. "
            "If LinkedIn text is thin, say so. GitHub repos are projects, not jobs unless company is stated.",
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    f"Source type: {kind}",
                    wrap_untrusted("current_profile", profile_text),
                    wrap_untrusted("imported", str(payload)[:8000]),
                ]
            ),
        },
    ]
    data = gateway.complete_json(messages, task="extract", plan=plan or "free")
    if not isinstance(data, dict):
        return fallback
    data.setdefault("suggested_skills", fallback["suggested_skills"])
    data.setdefault("suggested_projects", fallback["suggested_projects"])
    data.setdefault("disclaimer", fallback["disclaimer"])
    return data
