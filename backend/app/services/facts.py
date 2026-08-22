"""Refuse invented employers, titles, schools, projects, and tools."""

from __future__ import annotations

from typing import Any


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _allowed_set(values: list[str]) -> set[str]:
    return {_norm(v) for v in values if v and _norm(v)}


def facts_from_resume(content: dict[str, Any]) -> dict[str, list[str]]:
    companies, titles, projects, skills = [], [], [], []
    for item in content.get("experience") or []:
        if item.get("company"):
            companies.append(str(item["company"]))
        if item.get("title"):
            titles.append(str(item["title"]))
        skills.extend(item.get("technologies") or [])
    for item in content.get("projects") or []:
        if item.get("name"):
            projects.append(str(item["name"]))
        skills.extend(item.get("technologies") or [])
    block = content.get("skills") or {}
    if isinstance(block, dict):
        for v in block.values():
            if isinstance(v, list):
                skills.extend(str(x) for x in v)
    return {
        "companies": companies,
        "titles": titles,
        "projects": projects,
        "skills": skills,
    }


def merge_allowed(profile_facts: dict[str, list[str]], resume_facts: dict[str, list[str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    keys = set(profile_facts) | set(resume_facts)
    for key in keys:
        seen = []
        for item in (profile_facts.get(key) or []) + (resume_facts.get(key) or []):
            if item and item not in seen:
                seen.append(item)
        out[key] = seen
    return out


def _in_allowed(value: str, allowed: set[str]) -> bool:
    needle = _norm(value)
    if not needle:
        return True
    if needle in allowed:
        return True
    return any(needle in a or a in needle for a in allowed if len(a) > 3)


def fact_check_resume(content: dict[str, Any], allowed: dict[str, list[str]]) -> dict[str, Any]:
    """Drop or flag claims that are not in the profile/original resume."""
    flagged = list(content.get("flagged_missing") or [])
    companies = _allowed_set(allowed.get("companies") or [])
    titles = _allowed_set(allowed.get("titles") or [])
    projects = _allowed_set(allowed.get("projects") or [])
    skills = _allowed_set(allowed.get("skills") or [])
    schools = _allowed_set(allowed.get("schools") or [])
    degrees = _allowed_set(allowed.get("degrees") or [])

    clean_exp = []
    for item in content.get("experience") or []:
        company = str(item.get("company") or "")
        title = str(item.get("title") or "")
        if company and companies and not _in_allowed(company, companies):
            flagged.append(f"Removed unverified employer “{company}” — add it to your profile if it is real.")
            continue
        if title and titles and not _in_allowed(title, titles):
            flagged.append(f"Removed unverified title “{title}”.")
            continue
        techs = [t for t in (item.get("technologies") or []) if _in_allowed(str(t), skills) or not skills]
        dropped = [t for t in (item.get("technologies") or []) if t not in techs]
        if dropped:
            flagged.append("Removed unverified tools: " + ", ".join(map(str, dropped)))
        item = {**item, "technologies": techs}
        clean_exp.append(item)

    clean_proj = []
    for item in content.get("projects") or []:
        name = str(item.get("name") or "")
        if name and projects and not _in_allowed(name, projects):
            flagged.append(f"Removed unverified project “{name}”.")
            continue
        clean_proj.append(item)

    clean_edu = []
    for item in content.get("education") or []:
        school = str(item.get("institution") or "")
        degree = str(item.get("degree") or "")
        if school and schools and not _in_allowed(school, schools):
            flagged.append(f"Removed unverified school “{school}”.")
            continue
        if degree and degrees and not _in_allowed(degree, degrees):
            flagged.append(f"Removed unverified degree “{degree}”.")
            continue
        clean_edu.append(item)

    skills_block = content.get("skills") or {}
    if isinstance(skills_block, dict) and skills:
        cleaned_skills = {}
        for key, vals in skills_block.items():
            if not isinstance(vals, list):
                cleaned_skills[key] = vals
                continue
            keep, drop = [], []
            for v in vals:
                if _in_allowed(str(v), skills):
                    keep.append(v)
                else:
                    drop.append(v)
            cleaned_skills[key] = keep
            if drop:
                flagged.append(f"Removed unverified {key}: " + ", ".join(map(str, drop)))
        skills_block = cleaned_skills

    unique_flags = list(dict.fromkeys(flagged))
    return {
        **content,
        "experience": clean_exp,
        "projects": clean_proj,
        "education": clean_edu,
        "skills": skills_block,
        "flagged_missing": unique_flags,
    }
