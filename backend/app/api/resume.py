import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from sqlalchemy.orm.attributes import flag_modified

from app.agents.resume import ats_score, cover_letter, profile_to_resume_content, tailor_resume
from app.deps import CurrentUser, DbDep
from app.models import Resume
from app.schemas import ATSIn, CoverLetterIn, ResumeGenerateIn, ResumeUpdateIn, TailorIn
from app.services.billing import assert_template_allowed, assert_within_limit, consume, limits_for
from app.services.export import TEMPLATES, render_docx, render_markdown, render_pdf
from app.services.facts import fact_check_resume, facts_from_resume, merge_allowed
from app.services.parsers import extract_text, parse_resume_text
from app.services.profile import allowed_facts, ensure_profile, profile_to_text, recompute_scores
from app.services.storage import delete_path, save_bytes

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


def _out(r: Resume) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "version_type": r.version_type,
        "template": r.template,
        "source": r.source,
        "target_role": r.target_role,
        "content": r.content,
        "change_log": r.change_log,
        "last_ats": r.last_ats,
        "is_active": r.is_active,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


@router.get("/templates")
def templates(user: CurrentUser):
    allowed = set(limits_for(user).get("templates") or [])
    return [{"id": k, "name": v} for k, v in TEMPLATES.items() if k in allowed]


@router.get("")
def list_resumes(user: CurrentUser, db: DbDep):
    rows = db.query(Resume).filter_by(user_id=user.id, is_active=True).order_by(Resume.updated_at.desc()).all()
    return [_out(r) for r in rows]


@router.get("/{rid}")
def get_resume(rid: int, user: CurrentUser, db: DbDep):
    row = db.query(Resume).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    return _out(row)


def _latest_active(db: DbDep, user) -> Resume | None:
    return (
        db.query(Resume)
        .filter_by(user_id=user.id, is_active=True)
        .order_by(Resume.updated_at.desc())
        .first()
    )


def _can_replace_at_cap(limits: dict, active: int) -> bool:
    return active >= limits["active_resumes"] and limits["active_resumes"] <= 1


@router.post("/generate")
def generate(payload: ResumeGenerateIn, user: CurrentUser, db: DbDep):
    limits = limits_for(user)
    active = db.query(Resume).filter_by(user_id=user.id, is_active=True).count()
    replace = _latest_active(db, user) if _can_replace_at_cap(limits, active) else None
    if active >= limits["active_resumes"] and replace is None:
        raise HTTPException(402, "Active resume limit reached for your plan")
    if payload.template not in limits["templates"]:
        raise HTTPException(402, "That template is not on your plan")
    assert_within_limit(db, user, "resume_generations")
    profile = ensure_profile(db, user)
    content = profile_to_resume_content(
        user.full_name,
        user.email,
        {
            "city": profile.city,
            "country": profile.country,
            "professional_status": profile.professional_status,
            "summary": profile.summary,
            "headline": profile.headline,
            "linkedin_url": getattr(profile, "linkedin_url", "") or "",
            "github_username": getattr(profile, "github_username", "") or "",
            "skills": profile.skills,
            "experience": profile.experience,
            "education": profile.education,
            "projects": profile.projects,
            "career_goals": profile.career_goals,
        },
        payload.target_role,
        payload.template,
        plan=user.plan,
    )
    consume(db, user, "resume_generations")
    if replace:
        replace.title = payload.title or replace.title
        replace.version_type = payload.version_type
        replace.template = payload.template
        replace.source = "generated"
        replace.target_role = payload.target_role
        replace.content = content
        log = list(replace.change_log or [])
        log.append("Regenerated from career profile (replaced the Free-plan resume).")
        replace.change_log = log
        flag_modified(replace, "content")
        flag_modified(replace, "change_log")
        db.commit()
        db.refresh(replace)
        recompute_scores(db, user)
        return _out(replace)
    row = Resume(
        user_id=user.id,
        title=payload.title or f"{payload.version_type.replace('_', ' ').title()} resume",
        version_type=payload.version_type,
        template=payload.template,
        source="generated",
        target_role=payload.target_role,
        content=content,
        change_log=["Generated from career profile. No facts invented."],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    recompute_scores(db, user)
    return _out(row)


@router.post("/upload")
async def upload(user: CurrentUser, db: DbDep, file: UploadFile = File(...)):
    limits = limits_for(user)
    active = db.query(Resume).filter_by(user_id=user.id, is_active=True).count()
    replace = _latest_active(db, user) if _can_replace_at_cap(limits, active) else None
    if active >= limits["active_resumes"] and replace is None:
        raise HTTPException(402, "Active resume limit reached for your plan")
    assert_within_limit(db, user, "resume_uploads")
    data = await file.read()
    if len(data) > 8_000_000:
        raise HTTPException(400, "File too large (8MB max)")
    try:
        text = extract_text(file.filename or "resume.pdf", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        # pypdf / python-docx raise their own errors on damaged files.
        raise HTTPException(400, f"Could not read that file: {exc}") from exc
    parsed = parse_resume_text(text)
    try:
        # Stored before the row is written, so a disk or R2 outage cannot leave
        # a resume pointing at a file that was never saved.
        stored_path = save_bytes(data, file.filename or "resume.pdf", "resumes")
    except Exception as exc:
        raise HTTPException(502, "Could not store the uploaded file. Try again in a moment.") from exc
    consume(db, user, "resume_uploads")
    content = {
        "contact": parsed["contact"],
        "summary": parsed["summary"],
        "experience": parsed["experience"],
        "education": parsed["education"],
        "skills": parsed["skills"],
        "projects": parsed["projects"],
        "flagged_missing": [f"Could not detect: {x}" for x in parsed["missing_fields"]],
    }
    note = "Parsed from upload. Please review extracted fields — parsers miss formatting."
    if replace:
        if replace.file_path:
            delete_path(replace.file_path)
        replace.title = file.filename or replace.title
        replace.version_type = "master"
        replace.source = "uploaded"
        replace.content = content
        replace.file_path = stored_path
        log = list(replace.change_log or [])
        log.append("Replaced the Free-plan resume with an uploaded file.")
        replace.change_log = log
        flag_modified(replace, "content")
        flag_modified(replace, "change_log")
        db.commit()
        db.refresh(replace)
        recompute_scores(db, user)
        return _out(replace)
    row = Resume(
        user_id=user.id,
        title=file.filename or "Uploaded resume",
        version_type="master",
        template="ats_classic",
        source="uploaded",
        content=content,
        file_path=stored_path,
        change_log=[note],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    recompute_scores(db, user)
    return _out(row)


@router.put("/{rid}")
def update_resume(rid: int, payload: ResumeUpdateIn, user: CurrentUser, db: DbDep):
    row = db.query(Resume).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    data = payload.model_dump(exclude_none=True)
    if data.get("template") and data["template"] not in limits_for(user).get("templates", []):
        raise HTTPException(402, "That template is not on your plan")
    if "content" in data:
        # Hand edits go through the same fact check as generated output,
        # otherwise the anti-hallucination guarantee has a hole in the middle.
        profile = ensure_profile(db, user)
        allowed = merge_allowed(allowed_facts(user, profile), facts_from_resume(row.content or {}))
        data["content"] = fact_check_resume(data["content"], allowed)
        log = list(row.change_log or [])
        log.append("Section-level edit by user.")
        row.change_log = log
        flag_modified(row, "change_log")
    for k, v in data.items():
        setattr(row, k, v)
    if "content" in data:
        flag_modified(row, "content")
    db.commit()
    db.refresh(row)
    recompute_scores(db, user)
    return _out(row)


@router.post("/{rid}/duplicate")
def duplicate(rid: int, user: CurrentUser, db: DbDep):
    limits = limits_for(user)
    active = db.query(Resume).filter_by(user_id=user.id, is_active=True).count()
    if active >= limits["active_resumes"]:
        raise HTTPException(402, "Active resume limit reached for your plan")
    row = db.query(Resume).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    if row.template not in limits.get("templates", []):
        raise HTTPException(402, "That template is not on your plan")
    copy = Resume(
        user_id=user.id,
        title=f"{row.title} (copy)",
        version_type=row.version_type,
        template=row.template,
        source=row.source,
        target_role=row.target_role,
        content=row.content,
        change_log=list(row.change_log or []) + ["Duplicated."],
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return _out(copy)


@router.delete("/{rid}")
def delete_resume(rid: int, user: CurrentUser, db: DbDep):
    row = db.query(Resume).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    row.is_active = False
    if row.file_path:
        delete_path(row.file_path)
        row.file_path = ""
    db.commit()
    recompute_scores(db, user)
    return {"ok": True}


@router.post("/tailor")
def tailor(payload: TailorIn, user: CurrentUser, db: DbDep):
    limits = limits_for(user)
    active = db.query(Resume).filter_by(user_id=user.id, is_active=True).count()
    replace = _latest_active(db, user) if _can_replace_at_cap(limits, active) else None
    if active >= limits["active_resumes"] and replace is None:
        raise HTTPException(402, "Active resume limit reached for your plan")
    assert_within_limit(db, user, "tailorings")
    row = db.query(Resume).filter_by(id=payload.resume_id, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    allowed_templates = limits.get("templates") or ["ats_classic"]
    template = row.template if row.template in allowed_templates else allowed_templates[0]
    profile = ensure_profile(db, user)
    result = tailor_resume(
        row.content or {},
        payload.job_description,
        allowed_facts(user, profile),
        advanced=bool(limits.get("advanced_analysis")),
        plan=user.plan,
    )
    consume(db, user, "tailorings")
    title = f"Tailored — {payload.target_role or row.title}"
    log = list(row.change_log or []) + result["changes"]
    if replace:
        replace.title = title
        replace.version_type = "role_specific"
        replace.template = template
        replace.source = "tailored"
        replace.target_role = payload.target_role
        replace.content = result["content"]
        replace.change_log = log + ["Replaced the Free-plan resume with a tailored version."]
        flag_modified(replace, "content")
        flag_modified(replace, "change_log")
        db.commit()
        db.refresh(replace)
        return {**_out(replace), "keywords": result["keywords"], "changes": result["changes"]}
    tailored = Resume(
        user_id=user.id,
        title=title,
        version_type="role_specific",
        template=template,
        source="tailored",
        target_role=payload.target_role,
        content=result["content"],
        change_log=log,
    )
    db.add(tailored)
    db.commit()
    db.refresh(tailored)
    return {**_out(tailored), "keywords": result["keywords"], "changes": result["changes"]}


@router.post("/ats")
def ats(payload: ATSIn, user: CurrentUser, db: DbDep):
    assert_within_limit(db, user, "resume_analyses")
    row = db.query(Resume).filter_by(id=payload.resume_id, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    if not (payload.job_description or "").strip():
        raise HTTPException(400, "Paste a job description before running ATS.")
    consume(db, user, "resume_analyses")
    result = ats_score(row.content or {}, payload.job_description)
    row.last_ats = result
    db.commit()
    recompute_scores(db, user)
    return result


@router.post("/cover-letter")
def make_cover_letter(payload: CoverLetterIn, user: CurrentUser, db: DbDep):
    assert_within_limit(db, user, "cover_letters")
    row = db.query(Resume).filter_by(id=payload.resume_id, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    consume(db, user, "cover_letters")
    profile = ensure_profile(db, user)
    result = cover_letter(
        profile_to_text(user, profile),
        row.content or {},
        payload.job_description,
        payload.style,
        merge_allowed(allowed_facts(user, profile), facts_from_resume(row.content or {})),
        plan=user.plan,
    )
    return result


def _download_name(title: str, ext: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", (title or "resume").strip())[:80].strip("._") or "resume"
    return f"{base}.{ext}"


@router.get("/{rid}/export")
def export_resume(rid: int, user: CurrentUser, db: DbDep, fmt: str = "pdf"):
    row = db.query(Resume).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Resume not found")
    content = dict(row.content or {})
    if row.target_role:
        content["target_role"] = row.target_role
    if fmt in ("pdf", "docx", "md", "txt"):
        assert_template_allowed(user, row.template)
    if fmt == "pdf":
        try:
            data = render_pdf(content, row.template)
        except Exception as exc:
            raise HTTPException(500, f"Could not build the PDF ({exc}). Try another template or shorten a project line.") from exc
        return Response(
            data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{_download_name(row.title, "pdf")}"'},
        )
    if fmt == "docx":
        if not limits_for(user).get("docx_export"):
            raise HTTPException(402, "DOCX export is on Pro and Premium")
        try:
            data = render_docx(content, row.template)
        except Exception as exc:
            raise HTTPException(500, f"Could not build the Word file ({exc}).") from exc
        return Response(
            data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{_download_name(row.title, "docx")}"'},
        )
    if fmt == "md":
        return Response(render_markdown(content, row.template), media_type="text/markdown")
    if fmt == "txt":
        return Response(render_markdown(content, row.template), media_type="text/plain")
    raise HTTPException(400, "fmt must be pdf, docx, md, or txt")
