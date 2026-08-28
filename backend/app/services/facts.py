"""Refuse invented employers, titles, schools, projects, and tools."""

from __future__ import annotations

import re
from typing import Any


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _allowed_set(values: list[str]) -> set[str]:
    return {_norm(v) for v in values if v and _norm(v)}


def facts_from_resume(content: dict[str, Any]) -> dict[str, list[str]]:
    companies, titles, projects, skills = [], [], [], []
    schools, degrees = [], []
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
    # Education has to be included or a resume uploaded from a file loses its
    # schools the first time it is saved: the allowed set would only ever
    # contain what the career profile happens to list.
    for item in content.get("education") or []:
        if item.get("institution"):
            schools.append(str(item["institution"]))
        if item.get("degree"):
            degrees.append(str(item["degree"]))
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
        "schools": schools,
        "degrees": degrees,
    }


def facts_from_profile(profile: dict[str, Any]) -> dict[str, list[str]]:
    """The career profile stores experience, education, projects and skills in
    the same shape as resume content, so the same extraction applies."""
    return facts_from_resume(profile or {})


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
    """Whether a structured claim is backed by the profile or original resume.

    An empty allowed set is a deny, not a skip: otherwise a sparse profile lets
    the model invent employers that then become ground truth on the next save.
    """
    needle = _norm(value)
    if not needle:
        return True
    if not allowed:
        return False
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
        if company and not _in_allowed(company, companies):
            flagged.append(f"Removed unverified employer “{company}” — add it to your profile if it is real.")
            continue
        if title and not _in_allowed(title, titles):
            flagged.append(f"Removed unverified title “{title}”.")
            item = {**item, "title": ""}
        techs = [t for t in (item.get("technologies") or []) if _in_allowed(str(t), skills) or not skills]
        dropped = [t for t in (item.get("technologies") or []) if t not in techs]
        if dropped:
            flagged.append("Removed unverified tools: " + ", ".join(map(str, dropped)))
        item = {**item, "technologies": techs}
        clean_exp.append(item)

    clean_proj = []
    for item in content.get("projects") or []:
        name = str(item.get("name") or "")
        if name and not _in_allowed(name, projects):
            flagged.append(f"Removed unverified project “{name}”.")
            continue
        clean_proj.append(item)

    clean_edu = []
    for item in content.get("education") or []:
        school = str(item.get("institution") or "")
        degree = str(item.get("degree") or "")
        if school and not _in_allowed(school, schools):
            flagged.append(f"Removed unverified school “{school}”.")
            continue
        if degree and not _in_allowed(degree, degrees):
            flagged.append(f"Removed unverified degree “{degree}”.")
            item = {**item, "degree": ""}
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

    # Structured fields are only half the resume. An employer named in the
    # summary or in a bullet never passes through any of the checks above, so
    # the prose is scanned too — flagged rather than deleted, because there is
    # no safe way to edit a sentence automatically.
    prose = [str(content.get("summary") or "")]
    for item in clean_exp:
        prose.extend(str(b) for b in _bullet_text(item))
    for org in unverified_organizations("\n".join(p for p in prose if p), allowed):
        flagged.append(
            f"“{org}” appears in your wording but is not on your profile. Confirm it or reword the sentence."
        )

    unique_flags = list(dict.fromkeys(flagged))
    return {
        **content,
        "experience": clean_exp,
        "projects": clean_proj,
        "education": clean_edu,
        "skills": skills_block,
        "flagged_missing": unique_flags,
    }


def _bullet_text(item: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("achievements", "responsibilities", "bullets", "highlights"):
        value = item.get(key)
        if isinstance(value, list):
            out.extend(str(v) for v in value if v)
        elif isinstance(value, str) and value:
            out.append(value)
    if isinstance(item.get("description"), str) and item["description"]:
        out.append(item["description"])
    return out


# Capitalized words that follow "at"/"for" without naming an organization.
_ORG_STOPWORDS = {
    "i", "the", "a", "an", "this", "that", "your", "our", "my", "their", "you",
    "dear", "hiring", "team", "teams", "manager", "sincerely", "regards", "best",
    "thank", "thanks", "yours", "faithfully", "role", "position", "company",
    "organization", "scale", "least", "most", "now", "present", "work", "university",
    "school", "college", "time", "times", "speed", "once", "first", "last", "every",
    "each", "it", "them", "us", "me", "he", "she", "they", "we",
}

# The preposition may start a sentence, so it is matched case-insensitively —
# lowercase-only silently missed every claim like "At Google I…". The flag is
# scoped so the captured name still has to be genuinely capitalized.
_ORG_AFTER = re.compile(
    r"\b(?i:at|for|with|joined|from)[ \t]+((?:[A-Z][\w&'’-]*)(?:[ \t]+(?:of|and|&|the)?[ \t]*[A-Z][\w&'’-]*){0,3})"
)
_CONJUNCTION = re.compile(r"[ \t]+(?:and|&|or)[ \t]+")
# A name cannot span a sentence or a line, or "…SQL.\n\nSincerely" reads as one
# organization.
_SENTENCE = re.compile(r"[.\n!?;:,]+")


def unverified_organizations(text: str, allowed: dict[str, list[str]]) -> list[str]:
    """Organization-shaped names in prose that are not on the profile.

    Cover letters are free text, so unlike a resume there is nothing safe to
    delete — the honest move is to surface the claim for the user to confirm.
    Skills and titles count as known, otherwise "with Python and SQL" reads as
    an unverified employer.
    """
    known = _allowed_set(
        (allowed.get("companies") or [])
        + (allowed.get("schools") or [])
        + (allowed.get("projects") or [])
        + (allowed.get("skills") or [])
        + (allowed.get("titles") or [])
        + (allowed.get("degrees") or [])
        + (allowed.get("name") or [])
    )
    candidates: list[str] = []
    for sentence in _SENTENCE.split(text or ""):
        for match in _ORG_AFTER.finditer(sentence):
            # "with Python and SQL" is one match but two separate claims.
            candidates.extend(_CONJUNCTION.split(match.group(1)))

    found: list[str] = []
    for part in candidates:
        candidate = part.strip()
        words = candidate.split()
        if not words or len(candidate) < 3:
            continue
        if all(w.lower() in _ORG_STOPWORDS for w in words):
            continue
        if _in_allowed(candidate, known):
            continue
        if candidate not in found:
            found.append(candidate)
    return found


def fact_check_letter(result: dict[str, Any], allowed: dict[str, list[str]]) -> dict[str, Any]:
    """Flag (never silently rewrite) organizations a cover letter invented."""
    letter = str(result.get("letter") or "")
    flagged = list(result.get("flagged_missing") or [])
    for org in unverified_organizations(letter, allowed):
        flagged.append(
            f"“{org}” is not on your profile. Confirm it before sending, or remove the sentence."
        )
    return {**result, "flagged_missing": list(dict.fromkeys(flagged))}
