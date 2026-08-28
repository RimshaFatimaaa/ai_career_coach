from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm.attributes import flag_modified

from app.deps import CurrentUser, DbDep
from app.models import ProfileImport, Reminder
from app.services.analytics import analytics_payload
from app.services.billing import assert_within_limit, consume
from app.services.profile import ensure_profile, profile_to_text
from app.services.reminders import add_reminder, generate_from_activity, list_reminders
from app.services.social import analyze_import, fetch_github

router = APIRouter(prefix="/api", tags=["phase3"])


class GithubIn(BaseModel):
    handle: str


class LinkedInIn(BaseModel):
    text: str
    url: str = ""


class ReminderIn(BaseModel):
    title: str
    body: str = ""
    due_at: datetime | None = None


class ReminderPatch(BaseModel):
    done: bool | None = None


class ApplyImportIn(BaseModel):
    skills: bool = True
    projects: bool = True


@router.get("/analytics")
def analytics(user: CurrentUser, db: DbDep):
    return analytics_payload(db, user)


@router.get("/reminders")
def reminders(user: CurrentUser, db: DbDep, include_done: bool = False):
    return list_reminders(db, user, include_done=include_done)


@router.post("/reminders")
def create_reminder(payload: ReminderIn, user: CurrentUser, db: DbDep):
    row = add_reminder(db, user, payload.title, payload.body, payload.due_at)
    return {"id": row.id, "title": row.title, "due_at": row.due_at}


@router.post("/reminders/generate")
def generate_reminders(user: CurrentUser, db: DbDep):
    return generate_from_activity(db, user)


@router.patch("/reminders/{rid}")
def patch_reminder(rid: int, payload: ReminderPatch, user: CurrentUser, db: DbDep):
    row = db.query(Reminder).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Reminder not found")
    if payload.done is not None:
        row.done = payload.done
    db.commit()
    return {"id": row.id, "done": row.done}


@router.delete("/reminders/{rid}")
def delete_reminder(rid: int, user: CurrentUser, db: DbDep):
    row = db.query(Reminder).filter_by(id=rid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Reminder not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/imports")
def list_imports(user: CurrentUser, db: DbDep):
    rows = db.query(ProfileImport).filter_by(user_id=user.id).order_by(ProfileImport.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "source": r.source,
            "handle": r.handle,
            "analysis": r.analysis,
            "applied": r.applied,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/imports/github")
def import_github(payload: GithubIn, user: CurrentUser, db: DbDep):
    assert_within_limit(db, user, "profile_imports")
    try:
        raw = fetch_github(payload.handle)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"GitHub could not be reached ({exc}).") from exc
    profile = ensure_profile(db, user)
    analysis = analyze_import("github", raw, profile_to_text(user, profile), plan=user.plan)
    consume(db, user, "profile_imports")
    row = ProfileImport(user_id=user.id, source="github", handle=raw["handle"], raw=raw, analysis=analysis)
    db.add(row)
    profile.github_username = raw["handle"]
    db.commit()
    db.refresh(row)
    return {"id": row.id, "source": "github", "handle": raw["handle"], "raw": raw, "analysis": analysis}


@router.post("/imports/linkedin")
def import_linkedin(payload: LinkedInIn, user: CurrentUser, db: DbDep):
    text = (payload.text or "").strip()
    if len(text) < 40:
        raise HTTPException(400, "Paste at least a few lines from your LinkedIn About / Experience sections. LinkedIn blocks automated scraping.")
    assert_within_limit(db, user, "profile_imports")
    profile = ensure_profile(db, user)
    raw = {"source": "linkedin", "url": payload.url, "text": text[:12000]}
    analysis = analyze_import("linkedin", raw, profile_to_text(user, profile), plan=user.plan)
    consume(db, user, "profile_imports")
    handle = payload.url or "pasted-profile"
    row = ProfileImport(user_id=user.id, source="linkedin", handle=handle, raw=raw, analysis=analysis)
    db.add(row)
    if payload.url:
        profile.linkedin_url = payload.url
    db.commit()
    db.refresh(row)
    return {"id": row.id, "source": "linkedin", "analysis": analysis}


@router.post("/imports/{iid}/apply")
def apply_import(iid: int, payload: ApplyImportIn, user: CurrentUser, db: DbDep):
    row = db.query(ProfileImport).filter_by(id=iid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Import not found")
    profile = ensure_profile(db, user)
    analysis = row.analysis or {}
    if payload.skills:
        skills = dict(profile.skills or {})
        bucket = list(skills.get("tools") or [])
        for skill in analysis.get("suggested_skills") or []:
            name = str(skill).strip()
            if name and name not in bucket:
                bucket.append(name)
        skills["tools"] = bucket
        profile.skills = skills
        flag_modified(profile, "skills")
    if payload.projects:
        projects = list(profile.projects or [])
        names = {str(p.get("name") or "").lower() for p in projects}
        for item in analysis.get("suggested_projects") or []:
            name = str(item.get("name") or "").strip()
            if not name or name.lower() in names:
                continue
            projects.append(
                {
                    "name": name,
                    "description": item.get("description") or "",
                    "role": "Personal project",
                    "technologies": [],
                    "github": item.get("url") or "",
                }
            )
            names.add(name.lower())
        profile.projects = projects
        flag_modified(profile, "projects")
    row.applied = True
    db.commit()
    return {"ok": True, "applied": True}
