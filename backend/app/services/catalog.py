"""Role skill catalogs for any career — never silently fall back to AI Engineer."""

from __future__ import annotations

from typing import Any

LEVEL_RANK = {"missing": 0, "beginner": 1, "intermediate": 2, "strong": 3, "optional": 0}

ROLE_CATALOG: dict[str, dict] = {
    "ai engineer": {
        "label": "AI Engineer",
        "required": {
            "Python": "strong",
            "Machine Learning": "strong",
            "Deep Learning": "intermediate",
            "PyTorch or TensorFlow": "intermediate",
            "LangChain / LLM apps": "intermediate",
            "SQL": "intermediate",
            "Git": "intermediate",
            "APIs / FastAPI": "intermediate",
            "Vector databases": "beginner",
            "Docker": "intermediate",
            "Prompt engineering": "intermediate",
        },
        "optional": ["Kubernetes", "MLOps", "AWS/GCP"],
        "description": "Builds production AI features: models, LLM apps, retrieval, and reliable services.",
    },
    "data scientist": {
        "label": "Data Scientist",
        "required": {
            "Python": "strong",
            "SQL": "strong",
            "Statistics": "strong",
            "Machine Learning": "strong",
            "Pandas / NumPy": "strong",
            "Data visualization": "intermediate",
            "Experiment design": "intermediate",
            "Communication": "intermediate",
        },
        "optional": ["Spark", "Deep Learning"],
        "description": "Turns messy data into decisions with statistics, models, and storytelling.",
    },
    "software engineer": {
        "label": "Software Engineer",
        "required": {
            "One primary language": "strong",
            "Data structures & algorithms": "intermediate",
            "Git": "strong",
            "SQL": "intermediate",
            "APIs": "intermediate",
            "Testing": "intermediate",
            "System design": "beginner",
        },
        "optional": ["Docker", "Cloud"],
        "description": "Designs and ships reliable software.",
    },
    "data analyst": {
        "label": "Data Analyst",
        "required": {
            "SQL": "strong",
            "Excel / spreadsheets": "strong",
            "Data visualization": "intermediate",
            "Statistics basics": "intermediate",
            "Dashboarding": "intermediate",
            "Business communication": "intermediate",
        },
        "optional": ["Python", "dbt"],
        "description": "Finds patterns in data and explains them so teams can act.",
    },
    "product manager": {
        "label": "Product Manager",
        "required": {
            "User research": "intermediate",
            "Prioritization": "strong",
            "Writing specs / PRDs": "intermediate",
            "Stakeholder communication": "strong",
            "Metrics and outcomes": "intermediate",
            "Roadmapping": "intermediate",
        },
        "optional": ["SQL", "A/B testing"],
        "description": "Decides what to build and why, using evidence and alignment.",
    },
    "architect": {
        "label": "Architect",
        "required": {
            "Design process": "strong",
            "Drawing and drafting": "strong",
            "CAD (AutoCAD, Revit, or similar)": "intermediate",
            "Building codes and regulations": "intermediate",
            "3D visualization / model making": "intermediate",
            "Site analysis": "intermediate",
            "Construction documentation": "beginner",
            "Client presentation": "intermediate",
            "Portfolio of built or academic work": "strong",
        },
        "optional": ["Sustainability / green building", "Project management", "Urban design"],
        "description": "Designs buildings and spaces with drawings, codes, and a portfolio — not software engineering.",
    },
    "interior designer": {
        "label": "Interior Designer",
        "required": {
            "Spatial design": "strong",
            "Materials and finishes": "intermediate",
            "CAD or interior software": "intermediate",
            "Client briefing": "intermediate",
            "Budgeting": "beginner",
            "Portfolio": "strong",
        },
        "optional": ["Lighting design", "FF&E specification"],
        "description": "Shapes interior environments for people, budget, and brand.",
    },
    "artist": {
        "label": "Artist",
        "required": {
            "Visual fundamentals (form, color, composition)": "strong",
            "Chosen medium (paint, digital, sculpture, etc.)": "strong",
            "Portfolio / body of work": "strong",
            "Critique and revision": "intermediate",
            "Artist statement": "intermediate",
            "Exhibition or publication practice": "beginner",
            "Professional presentation of work": "intermediate",
        },
        "optional": ["Grant writing", "Teaching", "Studio management"],
        "description": "Makes and presents original work. Fit is about craft and portfolio, not Python.",
    },
    "graphic designer": {
        "label": "Graphic Designer",
        "required": {
            "Typography": "strong",
            "Layout and composition": "strong",
            "Adobe or equivalent (Illustrator, Figma, InDesign)": "intermediate",
            "Brand systems": "intermediate",
            "Portfolio": "strong",
            "Client feedback cycles": "intermediate",
        },
        "optional": ["Motion", "Web design"],
        "description": "Solves communication problems with type, image, and layout.",
    },
    "teacher": {
        "label": "Teacher",
        "required": {
            "Subject knowledge": "strong",
            "Lesson planning": "strong",
            "Classroom management": "intermediate",
            "Assessment and feedback": "intermediate",
            "Communication with families": "intermediate",
            "Inclusive practice": "beginner",
        },
        "optional": ["Curriculum design", "EdTech"],
        "description": "Helps learners meet outcomes through planning, presence, and assessment.",
    },
    "nurse": {
        "label": "Nurse",
        "required": {
            "Clinical fundamentals": "strong",
            "Patient communication": "strong",
            "Medication safety": "intermediate",
            "Documentation": "intermediate",
            "Infection control": "intermediate",
            "Team handover": "intermediate",
        },
        "optional": ["Specialty certification"],
        "description": "Delivers safe, documented patient care as part of a clinical team.",
    },
    "marketer": {
        "label": "Marketer",
        "required": {
            "Audience research": "intermediate",
            "Campaign planning": "strong",
            "Copy or content": "intermediate",
            "Analytics": "intermediate",
            "Channel execution": "intermediate",
            "Brand voice": "intermediate",
        },
        "optional": ["SEO", "Paid ads", "CRM"],
        "description": "Creates demand and measures whether the work moved the audience.",
    },
    "accountant": {
        "label": "Accountant",
        "required": {
            "Financial reporting": "strong",
            "Bookkeeping / ledgers": "strong",
            "Excel": "intermediate",
            "Tax or compliance basics": "intermediate",
            "Attention to detail": "strong",
            "Client or stakeholder communication": "intermediate",
        },
        "optional": ["ERP systems", "Audit"],
        "description": "Keeps the numbers accurate, timely, and explainable.",
    },
    "journalist": {
        "label": "Journalist",
        "required": {
            "Reporting and interviewing": "strong",
            "Writing under deadline": "strong",
            "Source verification": "strong",
            "Ethics and law basics": "intermediate",
            "Published clips": "intermediate",
        },
        "optional": ["Audio / video", "Data journalism"],
        "description": "Finds, checks, and tells stories the public can trust.",
    },
    "human resources": {
        "label": "Human Resources",
        "required": {
            "Hiring process": "intermediate",
            "Employee relations": "intermediate",
            "Policy and compliance": "intermediate",
            "Confidentiality": "strong",
            "Stakeholder communication": "strong",
        },
        "optional": ["HRIS", "Compensation"],
        "description": "Supports people and the organization within policy and law.",
    },
}

ALIASES = {
    "ai eng": "ai engineer",
    "artificial intelligence engineer": "ai engineer",
    "llm engineer": "ai engineer",
    "machine learning engineer": "ai engineer",
    "mle": "ai engineer",
    "ds": "data scientist",
    "swe": "software engineer",
    "software developer": "software engineer",
    "data analyst": "data analyst",
    "architecture": "architect",
    "architects": "architect",
    "architectural designer": "architect",
    "fine art": "artist",
    "fine arts": "artist",
    "fine-arts": "artist",
    "fine arts artist": "artist",
    "architecture student": "architect",
    "architectural intern": "architect",
    "fine artist": "artist",
    "painter": "artist",
    "visual artist": "artist",
    "graphic design": "graphic designer",
    "ui designer": "graphic designer",
    "interior design": "interior designer",
    "teacher": "teacher",
    "educator": "teacher",
    "nursing": "nurse",
    "rn": "nurse",
    "marketing": "marketer",
    "digital marketer": "marketer",
    "accounting": "accountant",
    "hr": "human resources",
    "hrm": "human resources",
    "product management": "product manager",
    "pm": "product manager",
}

_DYNAMIC: dict[str, dict] = {}


def normalize_role(name: str) -> str:
    key = " ".join((name or "").strip().lower().split())
    return ALIASES.get(key, key)


def craft_role(name: str) -> dict[str, Any]:
    label = " ".join((name or "Professional").split()).title()
    return {
        "label": label,
        "required": {
            f"{label} fundamentals": "strong",
            "Portfolio or body of work": "intermediate",
            "Industry tools": "intermediate",
            "Professional communication": "intermediate",
            "Project delivery": "intermediate",
            "Client or stakeholder collaboration": "intermediate",
            "Domain knowledge": "strong",
        },
        "optional": ["Business development", "Mentoring", "Leadership"],
        "description": f"A practicing {label}. Requirements are craft, portfolio, and delivery — not a default tech stack.",
        "source": "generic",
    }


def generate_role_via_llm(name: str, plan: str = "free") -> dict[str, Any] | None:
    from app.services.llm import SAFETY_PREAMBLE, gateway, wrap_untrusted

    if not gateway.enabled:
        return None
    data = gateway.complete_json(
        [
            {
                "role": "system",
                "content": SAFETY_PREAMBLE
                + "\nReturn JSON {label, description, required: {skill: level}, optional: [string]} "
                "with 8-12 required skills for THIS career only. level is strong, intermediate, or beginner. "
                "Do not include Python, machine learning, Docker, or Git unless the career is actually in computing. "
                "Skills must be what hiring managers in that field would recognize.",
            },
            {"role": "user", "content": wrap_untrusted("target_role", name)},
        ],
        task="career",
        plan=plan,
    )
    if not data or not isinstance(data.get("required"), dict) or not data["required"]:
        return None
    required = {}
    for skill, level in data["required"].items():
        lvl = str(level).lower()
        if lvl not in LEVEL_RANK:
            lvl = "intermediate"
        required[str(skill)] = lvl
    optional = data.get("optional") if isinstance(data.get("optional"), list) else []
    return {
        "label": str(data.get("label") or name).strip() or name.title(),
        "required": required,
        "optional": [str(x) for x in optional[:6]],
        "description": str(data.get("description") or f"Professional practice in {name}."),
        "source": "llm",
    }


TECH_TELLS = {
    "python",
    "machine learning",
    "docker",
    "pytorch or tensorflow",
    "langchain / llm apps",
    "vector databases",
    "git",
    "sql",
}


def roadmap_catalog_mismatch(target_role: str, skill_gap: list) -> bool:
    """True when a saved roadmap was built from the wrong career catalog (e.g. ML for architect)."""
    role = get_role(target_role)
    expected = {str(s).lower() for s in (role.get("required") or {})}
    stored = {str(g.get("skill") or "").lower() for g in (skill_gap or []) if g.get("skill")}
    if not stored or not expected:
        return False
    if stored & expected:
        return False
    if stored & TECH_TELLS and not (expected & TECH_TELLS):
        return True
    return stored.isdisjoint(expected)


def is_catalog_role(name: str) -> bool:
    return normalize_role(name) in ROLE_CATALOG


def get_role(name: str, plan: str = "free") -> dict[str, Any]:
    key = normalize_role(name)
    if key in ROLE_CATALOG:
        return ROLE_CATALOG[key]
    if key in _DYNAMIC:
        return _DYNAMIC[key]
    generated = generate_role_via_llm(name, plan=plan) or craft_role(name)
    _DYNAMIC[key] = generated
    return generated


def flatten_skills(skills: dict) -> list[str]:
    out: list[str] = []
    for value in (skills or {}).values():
        if isinstance(value, list):
            out.extend(str(x) for x in value if x)
        elif isinstance(value, str) and value:
            out.append(value)
    return out


_SKIP_OWNED = {"", "none", "n/a", "na", "-", "nothing"}


def collect_profile_skills(profile: Any) -> list[str]:
    """Skills, coursework, and tools from the whole profile — not just the skills box."""
    if profile is None:
        return []
    if isinstance(profile, dict):
        skills = profile.get("skills") or {}
        education = profile.get("education") or []
        experience = profile.get("experience") or []
        projects = profile.get("projects") or []
    else:
        skills = getattr(profile, "skills", None) or {}
        education = getattr(profile, "education", None) or []
        experience = getattr(profile, "experience", None) or []
        projects = getattr(profile, "projects", None) or []
    found: list[str] = []
    seen: set[str] = set()

    def add(items: Any) -> None:
        if items is None:
            return
        if isinstance(items, str):
            items = [p.strip() for p in items.split(",")]
        for raw in items:
            text = str(raw or "").strip()
            key = text.lower()
            if not text or key in _SKIP_OWNED or key.startswith("none yet"):
                continue
            if key in seen:
                continue
            seen.add(key)
            found.append(text)

    add(flatten_skills(skills if isinstance(skills, dict) else {}))
    for edu in education:
        if not isinstance(edu, dict):
            continue
        add(edu.get("coursework") or [])
        add([edu.get("major") or "", edu.get("degree") or ""])
    for exp in experience:
        if not isinstance(exp, dict):
            continue
        add(exp.get("technologies") or [])
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        add(proj.get("technologies") or [])
    return found


def infer_level(skill: str, owned: list[str]) -> str:
    skill_l = skill.lower()
    owned_l = [s.lower() for s in owned]
    for item in owned_l:
        if skill_l in item or item in skill_l:
            if any(tok in item for tok in ("advanced", "expert", "strong")):
                return "strong"
            return "intermediate"
        tokens = [t for t in skill_l.replace("/", " ").replace("-", " ").split() if len(t) > 2]
        if tokens and all(any(t in o for o in owned_l) for t in tokens[:2]):
            return "intermediate"
    synonyms = {
        "python": ["python"],
        "sql": ["sql", "postgres", "mysql"],
        "docker": ["docker", "container"],
        "langchain / llm apps": ["langchain", "langgraph", "llm", "rag"],
        "pytorch or tensorflow": ["pytorch", "tensorflow", "keras"],
        "machine learning": ["machine learning", "sklearn", "scikit"],
        "git": ["git", "github"],
        "apis / fastapi": ["fastapi", "api", "rest"],
        "cad (autocad, revit, or similar)": ["autocad", "revit", "sketchup", "rhino", "cad"],
        "drawing and drafting": ["drawing", "drafting", "sketch"],
        "portfolio": ["portfolio"],
        "typography": ["typography", "type"],
        "excel": ["excel", "spreadsheet"],
        "one primary language": ["python", "javascript", "java", "c++", "typescript", "go"],
    }
    for key, syns in synonyms.items():
        if key in skill_l or skill_l in key:
            if any(s in o for s in syns for o in owned_l):
                return "intermediate"
    return "missing"
