"""PDF/DOCX resume extraction — structured, never invented."""

from __future__ import annotations

import io
import re
from typing import Any


SECTION_ALIASES = {
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "education": ["education", "academic", "academics"],
    "skills": ["skills", "technical skills", "core skills"],
    "projects": ["projects", "personal projects", "selected projects"],
    "summary": ["summary", "profile", "objective", "about"],
    "certifications": ["certifications", "certificates", "licenses"],
}


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Upload PDF, DOCX, TXT, or MD.")


def parse_resume_text(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email = _first(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text))
    phone = _first(re.findall(r"(\+?\d[\d\s\-()]{8,}\d)", text))
    name = lines[0] if lines and "@" not in lines[0] and len(lines[0]) < 80 else ""
    sections = _split_sections(text)
    skills = _split_skills(sections.get("skills", ""))
    return {
        "contact": {"name": name, "email": email, "phone": phone},
        "summary": sections.get("summary", "")[:1200],
        "experience": _parse_experience(sections.get("experience", "")),
        "education": _parse_education(sections.get("education", "")),
        "skills": skills,
        "projects": _parse_projects(sections.get("projects", "")),
        "raw_text": text[:20000],
        "missing_fields": _missing(name, email, sections),
    }


def _first(items: list[str]) -> str:
    return items[0].strip() if items else ""


def _split_sections(text: str) -> dict[str, str]:
    headers = []
    for key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            for match in re.finditer(rf"^\s*{re.escape(alias)}\s*$", text, re.I | re.M):
                headers.append((match.start(), key))
    headers.sort()
    out: dict[str, str] = {}
    for i, (start, key) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        block = text[start:end]
        block = re.sub(r"^[^\n]+\n", "", block, count=1)
        out[key] = (out.get(key, "") + "\n" + block).strip()
    return out


def _split_skills(block: str) -> dict[str, list[str]]:
    tokens = re.split(r"[,•|/;\n]", block)
    items = [t.strip(" -") for t in tokens if 1 < len(t.strip()) < 40]
    return {
        "programming": [s for s in items if s.lower() in _LANGS or s.lower().endswith("script")],
        "frameworks": [s for s in items if s.lower() in _FRAMEWORKS],
        "tools": [s for s in items if s not in _LANGS],
        "platforms": [],
        "technical": items[:30],
        "soft": [],
        "certifications": [],
    }


def _parse_experience(block: str) -> list[dict]:
    if not block:
        return []
    chunks = re.split(r"\n{2,}", block)
    items = []
    for chunk in chunks[:8]:
        lines = [ln.strip("•- ") for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        items.append(
            {
                "company": lines[0][:120],
                "title": lines[1][:120] if len(lines) > 1 else "",
                "start_date": "",
                "end_date": "",
                "responsibilities": lines[2:6],
                "achievements": [],
                "technologies": [],
                "industry": "",
            }
        )
    return items


def _parse_education(block: str) -> list[dict]:
    if not block:
        return []
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return []
    return [
        {
            "degree": lines[0][:160],
            "institution": lines[1][:160] if len(lines) > 1 else "",
            "major": "",
            "start_date": "",
            "graduation_date": "",
            "gpa": "",
            "coursework": [],
        }
    ]


def _parse_projects(block: str) -> list[dict]:
    chunks = re.split(r"\n{2,}", block) if block else []
    out = []
    for chunk in chunks[:8]:
        lines = [ln.strip("•- ") for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        out.append(
            {
                "name": lines[0][:120],
                "description": " ".join(lines[1:4]),
                "technologies": [],
                "role": "",
                "results": "",
                "github": "",
                "demo": "",
            }
        )
    return out


def _missing(name: str, email: str, sections: dict) -> list[str]:
    flags = []
    if not name:
        flags.append("full name")
    if not email:
        flags.append("email")
    for key in ("experience", "education", "skills"):
        if not sections.get(key):
            flags.append(key)
    return flags


_LANGS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "r", "scala", "kotlin",
}
_FRAMEWORKS = {
    "react", "next.js", "django", "flask", "fastapi", "pytorch", "tensorflow", "langchain", "langgraph",
    "pandas", "numpy", "scikit-learn", "node.js",
}
