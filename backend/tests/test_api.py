"""End-to-end HTTP tests.

The unit suite covers agent logic in isolation; these exercise the routes as a
client sees them — auth, plan gating, ownership, and quotas.
"""

from __future__ import annotations

from itertools import count

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Conversation, Resume, Roadmap, UsageRecord, User
from app.services.billing import period_key

GOOD_PASSWORD = "Reasonab1e-Pass"
_emails = count(1)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def new_email() -> str:
    return f"user{next(_emails)}@smoketest.io"


def register(client: TestClient, email: str | None = None, password: str = GOOD_PASSWORD) -> tuple[str, str]:
    email = email or new_email()
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Person", "accept_terms": True},
    )
    assert res.status_code == 200, res.text
    return email, res.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def set_plan(email: str, plan: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        user.plan = plan
        db.commit()
    finally:
        db.close()


def set_usage(email: str, feature: str, value: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        row = db.query(UsageRecord).filter_by(user_id=user.id, feature=feature, period=period_key()).first()
        if row:
            row.count = value
        else:
            db.add(UsageRecord(user_id=user.id, feature=feature, period=period_key(), count=value))
        db.commit()
    finally:
        db.close()


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------


def test_health_is_public(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_health_hides_infrastructure_outside_development(client, monkeypatch):
    from app.main import settings

    monkeypatch.setattr(settings, "app_env", "production")
    body = client.get("/api/health").json()
    assert set(body) == {"ok", "app", "llm"}


def test_register_and_me(client):
    email, token = register(client)
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["plan"] == "free"


def test_register_records_terms_acceptance(client):
    email, _ = register(client)
    db = SessionLocal()
    try:
        assert db.query(User).filter_by(email=email).first().terms_accepted_at is not None
    finally:
        db.close()


def test_register_requires_accepting_terms(client):
    res = client.post(
        "/api/auth/register",
        json={"email": new_email(), "password": GOOD_PASSWORD, "full_name": "No Terms", "accept_terms": False},
    )
    assert res.status_code == 400


@pytest.mark.parametrize("password", ["short1", "password123", "aaaaaaaa1", "abcdefghij"])
def test_register_rejects_weak_passwords(client, password):
    res = client.post(
        "/api/auth/register",
        json={"email": new_email(), "password": password, "full_name": "Weak", "accept_terms": True},
    )
    assert res.status_code == 422, password


def test_register_rejects_duplicate_email(client):
    email, _ = register(client)
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": GOOD_PASSWORD, "full_name": "Dup", "accept_terms": True},
    )
    assert res.status_code == 409


def test_login_rejects_wrong_password(client):
    email, _ = register(client)
    res = client.post("/api/auth/login", json={"email": email, "password": "Wrong-Pass123"})
    assert res.status_code == 401


def test_seeded_admin_can_sign_in(client):
    res = client.post(
        "/api/auth/login", json={"email": "admin@careercoach.app", "password": "SeededAdmin123!"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["user"]["role"] == "admin"


def test_unauthenticated_requests_are_rejected(client):
    for path in ("/api/profile", "/api/dashboard", "/api/memory", "/api/resumes"):
        assert client.get(path).status_code == 401, path


def test_forgot_password_never_returns_the_reset_link(client, monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr("app.api.auth.send_mail", lambda to, subject, body: sent.append(body) or True)
    email, token = register(client)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert "reset_url" not in res.json()
    assert "token=" not in str(res.json())

    reset_token = sent[0].split("token=")[1].split()[0]
    done = client.post("/api/auth/reset-password", json={"token": reset_token, "password": "Brand-New-Pass9"})
    assert done.status_code == 200

    # The reset must invalidate sessions issued before it.
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "Brand-New-Pass9"}).status_code == 200


def test_forgot_password_is_silent_for_unknown_emails(client):
    res = client.post("/api/auth/forgot-password", json={"email": "nobody@smoketest.io"})
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_reset_password_rejects_a_bad_token(client):
    res = client.post("/api/auth/reset-password", json={"token": "nope", "password": GOOD_PASSWORD})
    assert res.status_code == 400


# --------------------------------------------------------------------------
# profile & account
# --------------------------------------------------------------------------


def test_profile_full_name_is_editable(client):
    _, token = register(client)
    res = client.put("/api/profile", json={"full_name": "Renamed Person", "city": "Lahore"}, headers=auth(token))
    assert res.status_code == 200
    assert res.json()["full_name"] == "Renamed Person"
    assert client.get("/api/profile", headers=auth(token)).json()["full_name"] == "Renamed Person"


def test_export_covers_every_data_type(client):
    _, token = register(client)
    body = client.get("/api/account/export", headers=auth(token)).json()
    for key in ("user", "profile", "resumes", "memories", "interviews", "roadmaps", "conversations", "reminders", "usage"):
        assert key in body, key


def test_delete_account_requires_the_password(client):
    email, token = register(client)
    assert client.request("DELETE", "/api/account", headers=auth(token)).status_code == 422
    wrong = client.request("DELETE", "/api/account", json={"password": "Not-It-1234"}, headers=auth(token))
    assert wrong.status_code == 403
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 200

    ok = client.request("DELETE", "/api/account", json={"password": GOOD_PASSWORD}, headers=auth(token))
    assert ok.status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": GOOD_PASSWORD}).status_code == 401


# --------------------------------------------------------------------------
# career memory (Pro gating)
# --------------------------------------------------------------------------


def test_memory_is_closed_to_free_accounts(client):
    _, token = register(client)
    assert client.get("/api/memory", headers=auth(token)).status_code == 402
    created = client.post(
        "/api/memory",
        json={"category": "direction", "key": "k", "value": "v"},
        headers=auth(token),
    )
    assert created.status_code == 402


def test_memory_works_on_pro_and_locks_again_after_downgrade(client):
    email, token = register(client)
    set_plan(email, "pro")
    created = client.post(
        "/api/memory",
        json={"category": "direction", "key": "studio-practice", "value": "Prefers studios"},
        headers=auth(token),
    )
    assert created.status_code == 200
    mid = created.json()["id"]
    assert len(client.get("/api/memory", headers=auth(token)).json()) == 1

    set_plan(email, "free")
    assert client.get("/api/memory", headers=auth(token)).status_code == 402
    assert client.patch(f"/api/memory/{mid}", json={"enabled": False}, headers=auth(token)).status_code == 402
    # Users must always be able to remove their own data.
    assert client.delete(f"/api/memory/{mid}", headers=auth(token)).status_code == 200


def test_memory_is_not_injected_into_a_free_chat():
    from app.services.profile import memory_text

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(plan="free").first()
        assert memory_text(db, user) == ""
    finally:
        db.close()


def test_memory_of_another_user_is_not_reachable(client):
    owner_email, owner_token = register(client)
    set_plan(owner_email, "pro")
    mid = client.post(
        "/api/memory",
        json={"category": "direction", "key": "private", "value": "secret"},
        headers=auth(owner_token),
    ).json()["id"]

    other_email, other_token = register(client)
    set_plan(other_email, "pro")
    assert client.patch(f"/api/memory/{mid}", json={"value": "x"}, headers=auth(other_token)).status_code == 404
    assert client.delete(f"/api/memory/{mid}", headers=auth(other_token)).status_code == 404


# --------------------------------------------------------------------------
# career chat
# --------------------------------------------------------------------------


def test_chat_keeps_its_first_title_and_enforces_the_cap(client):
    email, token = register(client)
    first = client.post("/api/career/chat", json={"message": "How do I become a data analyst?"}, headers=auth(token))
    assert first.status_code == 200
    cid = first.json()["conversation_id"]

    client.post(
        "/api/career/chat",
        json={"message": "And what about salaries?", "conversation_id": cid},
        headers=auth(token),
    )
    titles = {c["id"]: c["title"] for c in client.get("/api/career/conversations", headers=auth(token)).json()}
    assert titles[cid].startswith("How do I become")

    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    set_usage(email, "career_chats", usage["career_chats"]["limit"])
    blocked = client.post("/api/career/chat", json={"message": "one more"}, headers=auth(token))
    assert blocked.status_code == 402


def test_offline_demo_replies_do_not_cost_a_chat_credit(client):
    """With no model configured the coach returns canned text — not worth a credit."""
    _, token = register(client)
    body = client.post("/api/career/chat", json={"message": "How do I become a data analyst?"}, headers=auth(token)).json()
    assert body["demo"] is True
    assert body["metered"] is False
    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    assert usage["career_chats"]["used"] == 0


def test_a_live_reply_costs_a_chat_credit(client, monkeypatch):
    import app.api.career as career_api

    monkeypatch.setattr(
        career_api,
        "run_career_chat",
        lambda state: {"reply": "Start with SQL.", "intent": "chat", "demo": False},
    )
    _, token = register(client)
    body = client.post("/api/career/chat", json={"message": "Where do I start?"}, headers=auth(token)).json()
    assert body["metered"] is True
    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    assert usage["career_chats"]["used"] == 1


def test_a_second_chat_at_cap_does_not_leave_an_extra_thread(client, monkeypatch):
    import app.api.career as career_api

    monkeypatch.setattr(
        career_api,
        "run_career_chat",
        lambda state: {"reply": "Start with SQL.", "intent": "chat", "demo": False},
    )
    email, token = register(client)
    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    set_usage(email, "career_chats", usage["career_chats"]["limit"] - 1)
    first = client.post("/api/career/chat", json={"message": "Where do I start?"}, headers=auth(token))
    second = client.post("/api/career/chat", json={"message": "And then what?"}, headers=auth(token))
    assert first.status_code == 200
    assert second.status_code == 402
    assert len(client.get("/api/career/conversations", headers=auth(token)).json()) == 1


def test_chat_keeps_only_the_last_stored_turns(client):
    _, token = register(client)
    first = client.post("/api/career/chat", json={"message": "How do I become a data analyst?"}, headers=auth(token))
    cid = first.json()["conversation_id"]
    db = SessionLocal()
    try:
        row = db.get(Conversation, cid)
        row.messages = [{"role": "user", "content": "old"}, {"role": "assistant", "content": "old"}] * 50
        db.commit()
    finally:
        db.close()
    client.post(
        "/api/career/chat",
        json={"message": "What should I do next this week?", "conversation_id": cid},
        headers=auth(token),
    )
    stored = client.get(f"/api/career/conversations/{cid}", headers=auth(token)).json()["messages"]
    assert len(stored) == 80
    assert stored[-2]["role"] == "user"
    assert stored[-2]["content"].startswith("What should I do")


def test_a_model_outage_is_not_billed_or_stored(client, monkeypatch):
    import app.api.career as career_api

    monkeypatch.setattr(
        career_api,
        "run_career_chat",
        lambda state: {
            "reply": "I could not reach the language model. Try again in a moment.",
            "intent": "chat",
            "demo": False,
        },
    )
    _, token = register(client)
    res = client.post("/api/career/chat", json={"message": "Where do I start?"}, headers=auth(token))
    assert res.status_code == 503
    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    assert usage["career_chats"]["used"] == 0
    assert client.get("/api/career/conversations", headers=auth(token)).json() == []


def test_chat_rejects_an_unknown_conversation(client):
    _, token = register(client)
    r = client.post("/api/career/chat", json={"message": "hello there", "conversation_id": 999999}, headers=auth(token))
    assert r.status_code == 404


def test_chat_offers_memories_instead_of_saving_them(client):
    email, token = register(client)
    set_plan(email, "pro")
    body = client.post(
        "/api/career/chat",
        json={"message": "I want to move into data engineering next year."},
        headers=auth(token),
    ).json()
    assert "suggested_memories" in body
    # Nothing is written until the user confirms.
    assert client.get("/api/memory", headers=auth(token)).json() == []

    if body["suggested_memories"]:
        client.post("/api/career/memories/confirm", json={"memories": body["suggested_memories"]}, headers=auth(token))
        assert client.get("/api/memory", headers=auth(token)).json()


def test_chat_rejects_an_empty_message(client):
    _, token = register(client)
    assert client.post("/api/career/chat", json={"message": "   "}, headers=auth(token)).status_code == 400


# --------------------------------------------------------------------------
# roadmap
# --------------------------------------------------------------------------


@pytest.fixture()
def roadmap(client):
    _, token = register(client)
    row = client.post(
        "/api/career/roadmap",
        json={"target_role": "AI Engineer", "duration_unit": "weeks", "duration_value": 2},
        headers=auth(token),
    )
    assert row.status_code == 200, row.text
    return token, row.json()


def test_adding_a_task_does_not_rebuild_the_roadmap(client, roadmap):
    token, before = roadmap
    task_count = sum(len(m["tasks"]) for m in before["milestones"])

    res = client.patch(
        f"/api/career/roadmap/{before['id']}/tasks",
        json={"milestone_index": 0, "action": "add", "custom_text": "Read the transformer paper"},
        headers=auth(token),
    )
    assert res.status_code == 200, res.text
    after = res.json()

    assert after["target_role"] == before["target_role"]
    assert len(after["milestones"]) == len(before["milestones"])
    assert sum(len(m["tasks"]) for m in after["milestones"]) == task_count + 1
    titles = [t["title"] for t in after["milestones"][0]["tasks"]]
    assert "Read the transformer paper" in titles
    # Every generated task must survive.
    original = {t["id"] for m in before["milestones"] for t in m["tasks"]}
    kept = {t["id"] for m in after["milestones"] for t in m["tasks"]}
    assert original <= kept


def test_adding_a_task_needs_text(client, roadmap):
    token, row = roadmap
    res = client.patch(
        f"/api/career/roadmap/{row['id']}/tasks",
        json={"milestone_index": 0, "action": "add", "custom_text": "  "},
        headers=auth(token),
    )
    assert res.status_code == 400


def test_completing_and_removing_tasks(client, roadmap):
    token, row = roadmap
    tid = row["milestones"][0]["tasks"][0]["id"]
    done = client.patch(
        f"/api/career/roadmap/{row['id']}/tasks",
        json={"milestone_index": 0, "task_id": tid, "completed": True, "action": "complete"},
        headers=auth(token),
    ).json()
    assert done["milestones"][0]["tasks"][0]["completed"] is True

    removed = client.patch(
        f"/api/career/roadmap/{row['id']}/tasks",
        json={"milestone_index": 0, "task_id": tid, "action": "remove"},
        headers=auth(token),
    ).json()
    assert tid not in [t["id"] for t in removed["milestones"][0]["tasks"]]

    missing = client.patch(
        f"/api/career/roadmap/{row['id']}/tasks",
        json={"milestone_index": 0, "task_id": "does-not-exist", "action": "complete", "completed": True},
        headers=auth(token),
    )
    assert missing.status_code == 404


def test_roadmap_of_another_user_is_not_reachable(client, roadmap):
    _, row = roadmap
    _, other = register(client)
    assert client.get(f"/api/career/roadmap/{row['id']}", headers=auth(other)).status_code == 404
    assert client.delete(f"/api/career/roadmap/{row['id']}", headers=auth(other)).status_code == 404


# --------------------------------------------------------------------------
# resumes
# --------------------------------------------------------------------------


PROFILE_PAYLOAD = {
    "full_name": "Ada Rahman",
    "city": "Lahore",
    "country": "Pakistan",
    "summary": "Final-year AI student.",
    "skills": {"programming": ["Python", "SQL"], "tools": ["Git"]},
    "education": [{"degree": "BS Artificial Intelligence", "institution": "UMT Lahore"}],
    "experience": [{"company": "Nexus Labs", "title": "ML Intern", "technologies": ["Python"]}],
    "projects": [{"name": "Resume Ranker", "technologies": ["Python"]}],
    "career_goals": {"desired_role": "AI Engineer", "experience_level": "entry"},
}


@pytest.fixture()
def resume(client):
    email, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    res = client.post("/api/resumes/generate", json={"template": "ats_classic", "target_role": "AI Engineer"}, headers=auth(token))
    assert res.status_code == 200, res.text
    return email, token, res.json()


def test_manual_edits_are_fact_checked(client, resume):
    _, token, row = resume
    tampered = dict(row["content"])
    tampered["experience"] = [{"company": "Google", "title": "Staff Engineer", "technologies": ["Rust"]}]

    res = client.put(f"/api/resumes/{row['id']}", json={"content": tampered}, headers=auth(token))
    assert res.status_code == 200
    content = res.json()["content"]

    companies = [e.get("company") for e in content["experience"]]
    assert "Google" not in companies
    assert any("Google" in f for f in content["flagged_missing"])


def test_saving_an_uploaded_resume_keeps_its_education(client):
    """Uploaded schools are allowed facts too, not just whatever the profile lists."""
    _, token = register(client)
    client.put(
        "/api/profile",
        json={**PROFILE_PAYLOAD, "education": [{"degree": "BS CS", "institution": "FAST NUCES"}]},
        headers=auth(token),
    )
    uploaded = client.post(
        "/api/resumes/upload",
        files={"file": ("cv.txt", b"Ada Rahman\nEducation\nBS Artificial Intelligence, UMT Lahore\nSkills\nPython", "text/plain")},
        headers=auth(token),
    ).json()
    assert uploaded["content"]["education"]

    saved = client.put(
        f"/api/resumes/{uploaded['id']}", json={"content": uploaded["content"]}, headers=auth(token)
    ).json()
    assert saved["content"]["education"] == uploaded["content"]["education"]


def test_manual_edits_that_match_the_profile_are_kept(client, resume):
    _, token, row = resume
    edited = dict(row["content"])
    edited["summary"] = "Final-year AI student focused on retrieval systems."

    content = client.put(f"/api/resumes/{row['id']}", json={"content": edited}, headers=auth(token)).json()["content"]
    assert content["summary"].startswith("Final-year AI student focused")
    assert [e["company"] for e in content["experience"]] == ["Nexus Labs"]


def test_docx_export_is_gated_but_pdf_is_not(client, resume):
    email, token, row = resume
    assert client.get(f"/api/resumes/{row['id']}/export?fmt=pdf", headers=auth(token)).status_code == 200
    assert client.get(f"/api/resumes/{row['id']}/export?fmt=docx", headers=auth(token)).status_code == 402

    set_plan(email, "pro")
    assert client.get(f"/api/resumes/{row['id']}/export?fmt=docx", headers=auth(token)).status_code == 200


def test_free_plan_caps_active_resumes_and_delete_frees_a_slot(client, resume):
    _, token, row = resume
    assert client.post(f"/api/resumes/{row['id']}/duplicate", headers=auth(token)).status_code == 402
    assert client.delete(f"/api/resumes/{row['id']}", headers=auth(token)).status_code == 200
    assert client.get("/api/resumes", headers=auth(token)).json() == []


def test_duplicate_rejects_a_template_the_plan_lost(client, resume):
    email, token, row = resume
    set_plan(email, "pro")
    client.put(f"/api/resumes/{row['id']}", json={"template": "executive"}, headers=auth(token))
    set_plan(email, "free")
    res = client.post(f"/api/resumes/{row['id']}/duplicate", headers=auth(token))
    assert res.status_code == 402


def test_upload_is_metered_and_records_the_stored_file(client):
    email, token = register(client)
    files = {"file": ("resume.txt", b"Ada Rahman\nPython, SQL\nExperience\nNexus Labs", "text/plain")}
    res = client.post("/api/resumes/upload", files=files, headers=auth(token))
    assert res.status_code == 200, res.text

    assert client.get("/api/billing/usage", headers=auth(token)).json()["resume_uploads"]["used"] == 1

    db = SessionLocal()
    try:
        stored = db.query(Resume).filter_by(id=res.json()["id"]).first()
        assert stored.file_path
    finally:
        db.close()


def test_resume_of_another_user_is_not_reachable(client, resume):
    _, _, row = resume
    _, other = register(client)
    assert client.get(f"/api/resumes/{row['id']}", headers=auth(other)).status_code == 404
    assert client.put(f"/api/resumes/{row['id']}", json={"title": "stolen"}, headers=auth(other)).status_code == 404
    assert client.delete(f"/api/resumes/{row['id']}", headers=auth(other)).status_code == 404


def test_ats_notes_do_not_claim_to_be_ai_generated(client, resume):
    _, token, row = resume
    res = client.post(
        "/api/resumes/ats",
        json={"resume_id": row["id"], "job_description": "Python and SQL engineer"},
        headers=auth(token),
    )
    assert res.status_code == 200
    assert "ai-generated" not in " ".join(res.json()["notes"]).lower()


# --------------------------------------------------------------------------
# interviews
# --------------------------------------------------------------------------


@pytest.fixture()
def interview(client):
    email, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    res = client.post(
        "/api/interviews/start",
        json={"target_role": "AI Engineer", "question_count": 3},
        headers=auth(token),
    )
    assert res.status_code == 200, res.text
    return email, token, res.json()


def test_interview_rejects_an_empty_answer(client, interview):
    _, token, row = interview
    assert client.post(f"/api/interviews/{row['id']}/answer", json={"answer": "   "}, headers=auth(token)).status_code == 422
    assert client.post(f"/api/interviews/{row['id']}/answer", json={"answer": ""}, headers=auth(token)).status_code == 422


def test_interview_rejects_an_absurd_duration(client, interview):
    _, token, row = interview
    res = client.post(
        f"/api/interviews/{row['id']}/answer",
        json={"answer": "I led a project that shipped on time.", "duration_ms": 10**12},
        headers=auth(token),
    )
    assert res.status_code == 422


def test_typed_answers_do_not_get_speech_metrics(client, interview):
    _, token, row = interview
    res = client.post(
        f"/api/interviews/{row['id']}/answer",
        json={"answer": "At Nexus Labs I built a retrieval pipeline and cut latency in half.", "duration_ms": 5000},
        headers=auth(token),
    )
    assert res.status_code == 200
    db = SessionLocal()
    try:
        from app.models import InterviewSession

        session = db.get(InterviewSession, row["id"])
        assert "voice" not in session.questions[0]
    finally:
        db.close()


def test_voice_answer_attaches_speech_metrics_from_real_audio(client):
    email, token = register(client)
    set_plan(email, "premium")
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    row = client.post(
        "/api/interviews/start",
        json={"target_role": "AI Engineer", "question_count": 3, "mode": "voice"},
        headers=auth(token),
    ).json()
    res = client.post(
        f"/api/interviews/{row['id']}/voice-answer",
        data={"duration_ms": 4000, "transcript": "I led a retrieval pipeline and cut latency in half."},
        files={"audio": ("a.webm", b"\x00" * 512, "audio/webm")},
        headers=auth(token),
    )
    assert res.status_code == 200, res.text
    db = SessionLocal()
    try:
        from app.models import InterviewSession

        session = db.get(InterviewSession, row["id"])
        assert session.questions[0].get("voice")
        assert session.questions[0]["answer"].startswith("I led")
    finally:
        db.close()


def test_interview_cannot_be_ended_twice(client, interview):
    _, token, row = interview
    first = client.post(f"/api/interviews/{row['id']}/end", headers=auth(token))
    assert first.status_code == 200
    assert first.json()["status"] == "completed"

    second = client.post(f"/api/interviews/{row['id']}/end", headers=auth(token))
    assert second.status_code == 409

    assert client.post(
        f"/api/interviews/{row['id']}/answer", json={"answer": "late answer"}, headers=auth(token)
    ).status_code == 400


def test_interview_of_another_user_is_not_reachable(client, interview):
    _, _, row = interview
    _, other = register(client)
    assert client.get(f"/api/interviews/{row['id']}", headers=auth(other)).status_code == 404


# --------------------------------------------------------------------------
# reminders & admin
# --------------------------------------------------------------------------


def test_generated_reminders_spread_across_real_dates(client):
    _, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    client.post(
        "/api/career/roadmap",
        json={"target_role": "AI Engineer", "duration_unit": "weeks", "duration_value": 3},
        headers=auth(token),
    )
    rows = client.post("/api/reminders/generate", headers=auth(token)).json()
    assert rows
    assert len(rows) <= 20
    due_dates = {r["due_at"][:10] for r in rows if r["due_at"]}
    assert len(due_dates) > 1


def test_admin_routes_reject_normal_users(client):
    _, token = register(client)
    assert client.get("/api/admin/users", headers=auth(token)).status_code == 403


def test_login_is_rate_limited(client):
    """The limiter is off for the rest of the suite, so prove it works here."""
    from app.ratelimit import limiter

    limiter.enabled = True
    try:
        codes = [
            client.post(
                "/api/auth/login", json={"email": "nobody@smoketest.io", "password": "Whatever-123"}
            ).status_code
            for _ in range(12)
        ]
    finally:
        limiter.reset()
        limiter.enabled = False
    assert 429 in codes
    assert client.post("/api/auth/login", json={"email": "nobody@smoketest.io", "password": "x"}).status_code == 401


def test_mcp_tools_are_listed(client):
    _, token = register(client)
    res = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=auth(token))
    assert res.status_code == 200
    assert res.json()["result"]["tools"]


def test_mcp_reports_failures_as_jsonrpc_errors(client):
    """An MCP client cannot parse a FastAPI error body."""
    _, token = register(client)
    unknown_method = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 7, "method": "tools/nope"}, headers=auth(token)
    ).json()
    assert unknown_method["error"]["code"] == -32601
    assert unknown_method["id"] == 7

    no_name = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {}}, headers=auth(token)
    ).json()
    assert no_name["error"]["code"] == -32602


# --------------------------------------------------------------------------
# export gating and completeness
# --------------------------------------------------------------------------


def test_downgraded_user_cannot_export_a_paid_template(client):
    email, token = register(client)
    set_plan(email, "premium")
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    rid = client.post(
        "/api/resumes/generate", json={"template": "executive", "title": "Exec"}, headers=auth(token)
    ).json()["id"]
    assert client.get(f"/api/resumes/{rid}/export?fmt=pdf", headers=auth(token)).status_code == 200

    set_plan(email, "free")
    blocked = client.get(f"/api/resumes/{rid}/export?fmt=pdf", headers=auth(token))
    assert blocked.status_code == 402
    assert "executive" in blocked.json()["detail"].lower()


def test_markdown_export_is_not_missing_sections(client, resume):
    _, token, row = resume
    text = client.get(f"/api/resumes/{row['id']}/export?fmt=md", headers=auth(token)).text
    assert "## Projects" in text
    assert "## Education" in text
    assert "Nexus Labs" in text


# --------------------------------------------------------------------------
# quotas
# --------------------------------------------------------------------------


def test_skill_gap_and_roadmaps_are_metered(client):
    email, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    assert client.post("/api/career/skill-gap", json={"target_role": "AI Engineer"}, headers=auth(token)).status_code == 200

    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    assert usage["skill_gap_analyses"]["used"] == 1

    set_usage(email, "skill_gap_analyses", usage["skill_gap_analyses"]["limit"])
    assert client.post("/api/career/skill-gap", json={"target_role": "AI Engineer"}, headers=auth(token)).status_code == 402

    set_usage(email, "roadmaps", 5)
    blocked = client.post(
        "/api/career/roadmap",
        json={"target_role": "AI Engineer", "duration_unit": "weeks", "duration_value": 2},
        headers=auth(token),
    )
    assert blocked.status_code == 402


def test_consume_refuses_to_cross_the_cap(client):
    """The cap is re-tested inside the write, not only before it."""
    from app.services.billing import consume, limits_for

    email, _ = register(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        cap = limits_for(user)["cover_letters"]
        for _ in range(cap):
            consume(db, user, "cover_letters")
        with pytest.raises(HTTPException) as exc:
            consume(db, user, "cover_letters")
        assert exc.value.status_code == 402
    finally:
        db.close()


def test_usage_rows_cannot_duplicate_a_period(client):
    from sqlalchemy.exc import IntegrityError

    email, _ = register(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        db.add(UsageRecord(user_id=user.id, feature="cover_letters", period=period_key(), count=1))
        db.commit()
        db.add(UsageRecord(user_id=user.id, feature="cover_letters", period=period_key(), count=2))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_usage_does_not_leak_provider_names(client):
    _, token = register(client)
    assert "providers" not in client.get("/api/billing/usage", headers=auth(token)).json()


# --------------------------------------------------------------------------
# roadmap and memory hardening
# --------------------------------------------------------------------------


def test_negative_milestone_index_is_rejected(client):
    _, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    row = client.post(
        "/api/career/roadmap",
        json={"target_role": "AI Engineer", "duration_unit": "weeks", "duration_value": 2},
        headers=auth(token),
    ).json()
    res = client.patch(
        f"/api/career/roadmap/{row['id']}/tasks",
        json={"milestone_index": -1, "task_id": "", "action": "add", "custom_text": "sneaky"},
        headers=auth(token),
    )
    assert res.status_code == 400


def test_creating_the_same_memory_key_twice_updates_it(client):
    email, token = register(client)
    set_plan(email, "pro")
    body = {"category": "preference", "key": "target_city", "value": "Lahore", "enabled": True}
    client.post("/api/memory", json=body, headers=auth(token))
    client.post("/api/memory", json={**body, "value": "Karachi"}, headers=auth(token))
    rows = client.get("/api/memory", headers=auth(token)).json()
    assert len([r for r in rows if r["key"] == "target_city"]) == 1
    assert rows[0]["value"] == "Karachi"


# --------------------------------------------------------------------------
# voice entitlement
# --------------------------------------------------------------------------


def test_voice_endpoints_recheck_the_plan_after_a_downgrade(client):
    email, token = register(client)
    set_plan(email, "premium")
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    row = client.post(
        "/api/interviews/start",
        json={"target_role": "AI Engineer", "question_count": 3, "mode": "voice"},
        headers=auth(token),
    ).json()

    set_plan(email, "free")
    assert client.get(f"/api/interviews/{row['id']}/speak", headers=auth(token)).status_code == 402
    res = client.post(
        f"/api/interviews/{row['id']}/voice-answer",
        data={"duration_ms": 4000, "transcript": "An answer."},
        files={"audio": ("a.webm", b"\x00\x01", "audio/webm")},
        headers=auth(token),
    )
    assert res.status_code == 402


def test_login_retires_the_previous_token(client):
    email, old = register(client)
    fresh = client.post("/api/auth/login", json={"email": email, "password": GOOD_PASSWORD}).json()["access_token"]
    assert client.get("/api/auth/me", headers=auth(old)).status_code == 401
    assert client.get("/api/auth/me", headers=auth(fresh)).status_code == 200
    client.post("/api/auth/logout", headers=auth(fresh))
    assert client.get("/api/auth/me", headers=auth(fresh)).status_code == 401


def test_register_reserves_the_admin_email(client):
    res = client.post(
        "/api/auth/register",
        json={
            "email": "admin@careercoach.app",
            "password": GOOD_PASSWORD,
            "full_name": "Squatter",
            "accept_terms": True,
        },
    )
    assert res.status_code == 400


def test_mcp_skill_gap_respects_the_monthly_cap(client):
    email, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    set_usage(email, "skill_gap_analyses", 15)
    mcp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "analyze_skill_gap", "arguments": {"target_role": "AI Engineer"}},
        },
        headers=auth(token),
    ).json()
    assert "error" in mcp
    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    assert usage["skill_gap_analyses"]["used"] == 15


def test_markdown_export_is_gated_after_a_downgrade(client):
    email, token = register(client)
    set_plan(email, "premium")
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    rid = client.post(
        "/api/resumes/generate", json={"template": "two_tone", "title": "Paid"}, headers=auth(token)
    ).json()["id"]
    set_plan(email, "free")
    assert client.get(f"/api/resumes/{rid}/export?fmt=pdf", headers=auth(token)).status_code == 402
    assert client.get(f"/api/resumes/{rid}/export?fmt=md", headers=auth(token)).status_code == 402


def test_tailor_after_downgrade_uses_a_free_template(client):
    email, token = register(client)
    set_plan(email, "premium")
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    rid = client.post(
        "/api/resumes/generate", json={"template": "executive", "title": "Exec"}, headers=auth(token)
    ).json()["id"]
    set_plan(email, "free")
    tailored = client.post(
        "/api/resumes/tailor",
        json={"resume_id": rid, "job_description": "Looking for an intern who knows Python and SQL.", "target_role": "AI Engineer"},
        headers=auth(token),
    )
    assert tailored.status_code == 200, tailored.text
    assert tailored.json()["template"] in ("ats_classic", "graduate")


def test_empty_ats_does_not_consume_a_credit(client, resume):
    _, token, row = resume
    res = client.post("/api/resumes/ats", json={"resume_id": row["id"], "job_description": ""}, headers=auth(token))
    assert res.status_code == 422
    usage = client.get("/api/billing/usage", headers=auth(token)).json()
    assert usage["resume_analyses"]["used"] == 0


def test_stale_roadmap_refresh_keeps_progress(client):
    from sqlalchemy.orm.attributes import flag_modified

    email, token = register(client)
    client.put("/api/profile", json=PROFILE_PAYLOAD, headers=auth(token))
    created = client.post(
        "/api/career/roadmap",
        json={"target_role": "architecture", "duration_months": 3},
        headers=auth(token),
    )
    assert created.status_code == 200, created.text
    rid = created.json()["id"]
    first_id = created.json()["milestones"][0]["tasks"][0]["id"]
    client.patch(
        f"/api/career/roadmap/{rid}/tasks",
        json={"milestone_index": 0, "task_id": first_id, "completed": True},
        headers=auth(token),
    )
    client.patch(
        f"/api/career/roadmap/{rid}/tasks",
        json={"milestone_index": 0, "task_id": "", "action": "add", "custom_text": "KEEP-ME"},
        headers=auth(token),
    )
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        row = db.query(Roadmap).filter_by(id=rid, user_id=user.id).first()
        row.skill_gap = [{"skill": "Python"}, {"skill": "machine learning"}, {"skill": "Docker"}]
        flag_modified(row, "skill_gap")
        db.commit()
    finally:
        db.close()
    fetched = client.get(f"/api/career/roadmap/{rid}", headers=auth(token)).json()
    titles = [t.get("title") for m in fetched["milestones"] for t in (m.get("tasks") or [])]
    completed = [t for m in fetched["milestones"] for t in (m.get("tasks") or []) if t.get("completed")]
    assert "KEEP-ME" in titles
    assert completed
