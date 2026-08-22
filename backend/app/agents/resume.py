"""Resume generation, tailoring, ATS scoring, cover letters — with fact protection."""

from __future__ import annotations

import re
import secrets
from typing import Any

from app.services.facts import fact_check_resume, facts_from_resume, merge_allowed
from app.services.llm import SAFETY_PREAMBLE, gateway, wrap_untrusted


def profile_to_resume_content(
    user_name: str,
    email: str,
    profile: dict[str, Any],
    target_role: str = "",
    template: str = "ats_classic",
) -> dict[str, Any]:
    base = _profile_resume_base(user_name, email, profile, target_role)
    return polish_resume_content(base, profile, target_role, template)


def _profile_resume_base(user_name: str, email: str, profile: dict[str, Any], target_role: str = "") -> dict[str, Any]:
    raw_summary = (profile.get("summary") or "").strip()
    if raw_summary.lower() in {"", "nothing", "n/a", "na", "-", "none"}:
        summary = ""
    else:
        summary = raw_summary
    links = "  |  ".join(
        x
        for x in [
            profile.get("linkedin_url") or "",
            f"github.com/{profile['github_username']}" if profile.get("github_username") else "",
        ]
        if x
    )
    return {
        "contact": {
            "name": user_name,
            "email": email,
            "phone": "",
            "location": ", ".join(x for x in [profile.get("city"), profile.get("country")] if x),
            "links": links,
            "headline": profile.get("headline") or target_role,
        },
        "summary": summary,
        "skills": profile.get("skills") or {},
        "experience": profile.get("experience") or [],
        "education": profile.get("education") or [],
        "projects": profile.get("projects") or [],
        "flagged_missing": _flag_missing(profile),
    }


def polish_resume_content(
    content: dict[str, Any],
    profile: dict[str, Any],
    target_role: str = "",
    template: str = "ats_classic",
) -> dict[str, Any]:
    """Professional rewrite that stays inside profile facts. Wording changes every run."""
    variant = secrets.randbelow(4)
    if gateway.enabled:
        rewritten = _llm_resume_pass(content, target_role, template, variant)
        if rewritten:
            return rewritten
    return _variant_resume(content, profile, target_role, template, variant)


def _llm_resume_pass(content: dict[str, Any], target_role: str, template: str, variant: int) -> dict[str, Any] | None:
    angles = (
        "lead with outcomes already on the profile",
        "lead with tools and methods already listed",
        "lead with education and projects",
        "lead with the target role and evidenced overlap",
    )
    data = gateway.complete_json(
        [
            {
                "role": "system",
                "content": SAFETY_PREAMBLE
                + "\nYou are the Resume Agent. Rewrite this resume so it reads professionally and is not a copy of the last draft. "
                f"Angle: {angles[variant % 4]}. Template hint: {template}. Target role: {target_role or 'from profile'}. "
                "Return JSON {summary, experience, skills, projects, education, changes}. "
                "Only use facts already in the resume. Never invent employers, titles, dates, metrics, or tools. "
                "Experience items keep company, title, dates; rewrite responsibilities/achievements as strong verb bullets.",
            },
            {"role": "user", "content": wrap_untrusted("resume", str(content))},
        ],
        task="resume",
    )
    if not data:
        return None
    merged = {**content}
    for key in ("summary", "experience", "skills", "projects", "education"):
        if data.get(key):
            merged[key] = data[key]
    allowed = merge_allowed({}, facts_from_resume(content))
    merged = fact_check_resume(merged, allowed)
    merged["flagged_missing"] = list(dict.fromkeys((content.get("flagged_missing") or []) + (data.get("flagged_missing") or [])))
    merged["variant"] = variant
    return merged


def _variant_resume(
    content: dict[str, Any],
    profile: dict[str, Any],
    target_role: str,
    template: str,
    variant: int,
) -> dict[str, Any]:
    skills = dict(content.get("skills") or {})
    skill_list = [s for group in skills.values() if isinstance(group, list) for s in group if s]
    role = target_role or (profile.get("career_goals") or {}).get("desired_role") or (content.get("contact") or {}).get("headline") or "this role"
    industry = (profile.get("career_goals") or {}).get("desired_industry") or ""
    base = (content.get("summary") or "").strip()
    top = ", ".join(skill_list[:6])
    shapes = [
        f"{role} candidate. {base} Tools in use: {top}.".strip(),
        f"{base} Recent work centers on {top}." if base else f"Building toward {role} with {top}.",
        f"{'Student' if (profile.get('professional_status') == 'student') else 'Professional'} targeting {role}. {base} {('Industry: ' + industry + '.') if industry else ''}".strip(),
        f"{base} Seeking {role} work{(' in ' + industry) if industry else ''}.".strip() if base else f"Targeting {role} roles. Skills: {top}.",
    ]
    summary = " ".join(shapes[variant % 4].split())
    order = list(skills.keys())
    if variant % 2:
        order = list(reversed(order))
    rotated = {k: skills[k] for k in order if k in skills}
    experience = []
    for exp in content.get("experience") or []:
        row = dict(exp)
        resp = list(row.get("responsibilities") or [])
        ach = list(row.get("achievements") or [])
        if variant % 2:
            row["responsibilities"] = ach + resp
            row["achievements"] = []
        else:
            row["responsibilities"] = [_strong_bullet(x, variant) for x in resp]
            row["achievements"] = [_strong_bullet(x, variant) for x in ach]
        experience.append(row)
    projects = list(content.get("projects") or [])
    if variant % 2:
        projects = list(reversed(projects))
    out = {
        **content,
        "summary": summary,
        "skills": rotated,
        "experience": experience,
        "projects": projects,
        "variant": variant,
        "template_hint": template,
    }
    return out


def _strong_bullet(line: str, variant: int) -> str:
    text = (line or "").strip()
    if not text:
        return text
    verbs = (("Built", "Led", "Shipped"), ("Delivered", "Owned", "Implemented"), ("Created", "Ran", "Documented"))[variant % 3]
    parts = text.split(None, 1)
    if len(parts) == 2 and parts[0][:1].isupper():
        return f"{verbs[hash(text) % len(verbs)]} {parts[1]}"
    return f"{verbs[0]} {text}"


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in ("", "nothing", "n/a", "na", "-", "none")
    if isinstance(value, list):
        return any(_nonempty(v) for v in value)
    if isinstance(value, dict):
        return any(_nonempty(v) for v in value.values())
    return True


def _flag_missing(profile: dict[str, Any]) -> list[str]:
    flags = []
    if not _nonempty(profile.get("experience")):
        flags.append("No work experience on file — internships, freelance, volunteer, or studio roles can be added.")
    if not _nonempty(profile.get("projects")):
        flags.append("No projects listed — add 1–2 with your role and a result.")
    if not _nonempty(profile.get("summary")):
        flags.append("No professional summary yet — a 3-line summary helps ATS and humans.")
    skills = profile.get("skills") or {}
    if not any(_nonempty(v) for v in skills.values()):
        flags.append("Skills list is empty.")
    for exp in profile.get("experience") or []:
        if not exp.get("achievements") and not exp.get("responsibilities"):
            flags.append(f"Role at {exp.get('company') or 'unknown company'} has no bullets.")
    return flags


def tailor_resume(
    content: dict[str, Any],
    job_description: str,
    allowed_facts: dict[str, Any],
    advanced: bool = False,
) -> dict[str, Any]:
    keywords = extract_keywords(job_description)
    if gateway.enabled:
        messages = [
            {
                "role": "system",
                "content": SAFETY_PREAMBLE
                + "\nYou are the Resume Agent. Rewrite resume bullets to match the job description. "
                "Return JSON with keys: summary (string), experience (array of {company,title,start_date,end_date,responsibilities,achievements,technologies}), "
                "skills (object), changes (array of strings), flagged_missing (array of strings). "
                "You MUST only use facts from allowed_facts and the original resume. Never invent employers, titles, dates, metrics, or tools.",
            },
            {
                "role": "user",
                "content": "\n\n".join(
                    [
                        wrap_untrusted("allowed_facts", str(allowed_facts)),
                        wrap_untrusted("original_resume", str(content)),
                        wrap_untrusted("job_description", job_description),
                    ]
                ),
            },
        ]
        data = gateway.complete_json(messages, task="tailor", advanced=advanced)
        if data:
            merged = {**content, **{k: data[k] for k in ("summary", "experience", "skills") if k in data}}
            merged["projects"] = data.get("projects") or content.get("projects") or []
            merged["education"] = data.get("education") or content.get("education") or []
            allowed = merge_allowed(allowed_facts, facts_from_resume(content))
            merged = fact_check_resume(merged, allowed)
            extra_flags = data.get("flagged_missing") or []
            merged["flagged_missing"] = list(dict.fromkeys((merged.get("flagged_missing") or []) + extra_flags))
            changes = data.get("changes") or ["Rewrote summary and bullets toward the job description."]
            changes.append("Ran fact-check: unverified employers, titles, tools, and projects were removed.")
            return {"content": merged, "changes": changes, "keywords": keywords}
    # Deterministic fallback: reorder skills, prepend keyword-aware summary note
    skills = content.get("skills") or {}
    tech = list(skills.get("technical") or []) + list(skills.get("programming") or [])
    overlap = [k for k in keywords if any(k.lower() in t.lower() for t in tech)]
    summary = content.get("summary") or ""
    note = (
        f"Targeting this role with overlapping skills: {', '.join(overlap[:8])}."
        if overlap
        else "Keyword overlap with this posting is limited — consider adding evidenced skills to your profile first."
    )
    flagged = list(content.get("flagged_missing") or [])
    missing_kw = [k for k in keywords[:12] if not any(k.lower() in t.lower() for t in tech)]
    if missing_kw:
        flagged.append("Job asks for skills not in your profile: " + ", ".join(missing_kw[:8]) + ". Not added, because they were not evidenced.")
    new_content = {**content, "summary": (summary + " " + note).strip(), "flagged_missing": flagged}
    return {
        "content": new_content,
        "changes": ["Adjusted summary toward the job description.", "Did not invent missing skills or employers."],
        "keywords": keywords,
    }


def ats_score(content: dict[str, Any], job_description: str = "") -> dict[str, Any]:
    text = _flatten(content).lower()
    keywords = extract_keywords(job_description) if job_description else []
    hits = [k for k in keywords if k.lower() in text]
    had_jd = bool(keywords)
    if had_jd:
        keyword_align = round(100 * len(hits) / max(len(keywords), 1), 1)
    else:
        keyword_align = 0.0
    skills = content.get("skills") or {}
    skill_n = sum(len(v) for v in skills.values() if isinstance(v, list) and _nonempty(v))
    skill_cov = min(95, skill_n * 8) if skill_n else 0.0
    exp_n = len([e for e in (content.get("experience") or []) if _nonempty(e)])
    proj_n = len([p for p in (content.get("projects") or []) if _nonempty(p)])
    exp_rel = min(95, exp_n * 15 + proj_n * 10)
    formatting = 0
    contact = content.get("contact") or {}
    if _nonempty(contact.get("name")):
        formatting += 25
    if _nonempty(contact.get("email")):
        formatting += 25
    if _nonempty(content.get("education")):
        formatting += 25
    if _nonempty(content.get("summary")):
        formatting += 25
    completeness = 0.0
    if _nonempty(content.get("summary")):
        completeness += 16
    if exp_n:
        completeness += 28
    if _nonempty(content.get("education")):
        completeness += 16
    if skill_n:
        completeness += 20
    if proj_n:
        completeness += 20
    completeness = min(100.0, completeness)
    role_align = round((keyword_align * 0.5 + skill_cov * 0.3 + exp_rel * 0.2), 1) if had_jd else completeness
    if had_jd:
        ats = round(
            0.35 * keyword_align + 0.2 * skill_cov + 0.2 * exp_rel + 0.1 * formatting + 0.15 * role_align,
            1,
        )
    else:
        ats = round(completeness * 0.85 + formatting * 0.15, 1)
    notes = [
        "Scores are AI-generated estimates for personal tracking, not a guarantee of ATS passage or interviews.",
        "No facts were invented. Missing keywords are listed so you can add only what is true.",
    ]
    if not had_jd:
        notes.insert(0, "Paste a job description to score keyword fit. Completeness alone is not a hiring prediction.")
    return {
        "ats_readiness": ats,
        "keyword_alignment": keyword_align,
        "skill_coverage": round(skill_cov, 1),
        "experience_relevance": round(exp_rel, 1),
        "formatting": round(formatting, 1),
        "role_alignment": role_align,
        "matched_keywords": hits[:20],
        "missing_keywords": [k for k in keywords if k not in hits][:15],
        "had_jd": had_jd,
        "notes": notes,
        "flagged_missing": content.get("flagged_missing") or [],
    }


def extract_keywords(job_description: str) -> list[str]:
    stop = {
        "and", "the", "with", "for", "you", "our", "are", "will", "this", "that", "from", "have",
        "your", "job", "role", "work", "team", "ability", "strong", "experience", "years", "plus",
        "etc", "using", "including", "such", "other", "about", "into", "their",
    }
    tokens = re.findall(r"[A-Za-z][A-Za-z+#.]{1,}", job_description)
    seen = []
    for t in tokens:
        low = t.lower()
        if low in stop or len(low) < 2:
            continue
        if t[0].isupper() or low in _SKILLISH:
            if t not in seen:
                seen.append(t)
    return seen[:40]


_SKILLISH = {
    "python", "sql", "java", "react", "docker", "aws", "gcp", "azure", "kubernetes", "git",
    "pytorch", "tensorflow", "langchain", "fastapi", "django", "pandas", "excel", "tableau",
    "communication", "leadership", "testing", "ci", "cd", "linux", "api", "mlops", "rag",
}


def _flatten(content: dict[str, Any]) -> str:
    return str(content)


def cover_letter(
    profile_text: str,
    resume_content: dict[str, Any],
    job_description: str,
    style: str,
    allowed_facts: dict[str, Any],
) -> dict[str, Any]:
    styles = {
        "professional": "Formal, confident, 3 short paragraphs.",
        "concise": "Under 180 words, direct.",
        "technical": "Lead with systems, stacks, and projects.",
        "graduate": "Emphasize coursework, projects, and coachability.",
        "career-switcher": "Map transferable skills; do not overclaim domain years.",
    }
    instruction = styles.get(style, styles["professional"])
    if gateway.enabled:
        messages = [
            {
                "role": "system",
                "content": SAFETY_PREAMBLE
                + f"\nWrite a cover letter. Style: {instruction} Return JSON {{letter, flagged_missing}}. "
                "Ground ONLY in allowed facts, resume, and the job description. Never invent.",
            },
            {
                "role": "user",
                "content": "\n\n".join(
                    [
                        wrap_untrusted("allowed_facts", str(allowed_facts)),
                        wrap_untrusted("profile", profile_text),
                        wrap_untrusted("resume", str(resume_content)),
                        wrap_untrusted("job_description", job_description),
                    ]
                ),
            },
        ]
        data = gateway.complete_json(messages, task="resume")
        if data and data.get("letter"):
            return data
    name = (resume_content.get("contact") or {}).get("name") or "the candidate"
    return {
        "letter": (
            f"Dear Hiring Team,\n\nI am writing to apply for this role. {name}’s background "
            "matches several requirements in your posting, based only on the profile on file. "
            "I would welcome the chance to discuss how those evidenced skills transfer to your team.\n\n"
            "Sincerely,\n" + name
        ),
        "flagged_missing": ["Live LLM cover letters need LLM_API_KEY; this is a grounded stub."],
        "style": style,
    }
