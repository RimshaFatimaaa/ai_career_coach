from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm.attributes import flag_modified

from app.agents.interview import apply_followup, build_report, evaluate_answer, plan_questions
from app.deps import CurrentUser, DbDep
from app.models import InterviewSession
from app.schemas import InterviewAnswerIn, InterviewStartIn
from app.services.billing import assert_within_limit, consume, limits_for
from app.services.profile import ensure_profile, profile_to_text, recompute_scores
from app.services.voice import analyze_speech, synthesize_speech, transcribe_audio

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def _out(row: InterviewSession) -> dict:
    qs = list(row.questions or [])
    planned = int((qs[0].get("session_total") if qs else 0) or len(qs))
    if len(qs) > planned:
        qs = qs[:planned]
    current = None
    if row.status == "in_progress" and row.current_index < len(qs):
        q = qs[row.current_index]
        current = {"index": q.get("index"), "type": q.get("type"), "prompt": q.get("prompt"), "is_followup": q.get("is_followup")}
    return {
        "id": row.id,
        "target_role": row.target_role,
        "interview_type": row.interview_type,
        "mode": getattr(row, "mode", None) or (qs[0].get("session_mode") if qs else None) or "text",
        "status": row.status,
        "current_index": row.current_index,
        "total": planned,
        "planned_count": planned,
        "current_question": current,
        "answered": sum(1 for q in qs if q.get("answer")),
        "overall_score": row.overall_score,
        "report": row.report,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def _finish_answer(row, qs, evaluation, user, db):
    row.questions = qs
    flag_modified(row, "questions")
    row.current_index += 1
    planned = int((qs[0].get("session_total") if qs else 0) or len(qs))
    finished = row.current_index >= min(len(qs), planned)
    if finished:
        report = build_report(qs, row.target_role)
        row.report = report
        row.overall_score = report.get("overall")
        row.status = "completed"
        row.completed_at = datetime.now(timezone.utc)
        db.commit()
        recompute_scores(db, user)
        return {**_out(row), "evaluation": evaluation, "finished": True}
    db.commit()
    db.refresh(row)
    return {**_out(row), "evaluation": evaluation, "finished": False}


@router.get("")
def list_interviews(user: CurrentUser, db: DbDep):
    rows = (
        db.query(InterviewSession)
        .filter_by(user_id=user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return [_out(r) for r in rows]


@router.get("/{iid}")
def get_interview(iid: int, user: CurrentUser, db: DbDep):
    row = db.query(InterviewSession).filter_by(id=iid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Interview not found")
    data = _out(row)
    data["questions"] = row.questions
    data["job_description"] = row.job_description
    return data


@router.post("/start")
def start(payload: InterviewStartIn, user: CurrentUser, db: DbDep):
    mode = payload.mode if payload.mode in ("text", "voice") else "text"
    if mode == "voice" and not limits_for(user).get("voice_interviews"):
        raise HTTPException(402, "Voice interviews are on the Premium plan.")
    assert_within_limit(db, user, "mock_interviews")
    count = max(3, min(payload.question_count, 12))
    assert_within_limit(db, user, "interview_questions", count)
    profile = ensure_profile(db, user)
    recent = (
        db.query(InterviewSession)
        .filter_by(user_id=user.id)
        .order_by(InterviewSession.created_at.desc())
        .limit(6)
        .all()
    )
    avoid = []
    for sess in recent:
        for q in sess.questions or []:
            prompt = (q or {}).get("prompt") if isinstance(q, dict) else None
            if prompt:
                avoid.append(str(prompt))
    questions = plan_questions(
        payload.target_role,
        payload.interview_type,
        count,
        profile_to_text(user, profile),
        payload.job_description,
        avoid_prompts=avoid[:24],
    )
    if questions:
        questions[0]["session_mode"] = mode
        questions[0]["session_total"] = questions[0].get("session_total") or count
    row = InterviewSession(
        user_id=user.id,
        target_role=payload.target_role,
        interview_type=payload.interview_type,
        job_description=payload.job_description,
        questions=questions,
        status="in_progress",
        current_index=0,
        mode=mode,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    consume(db, user, "mock_interviews")
    consume(db, user, "interview_questions", count)
    return _out(row)


@router.get("/{iid}/speak")
def speak_question(iid: int, user: CurrentUser, db: DbDep):
    row = db.query(InterviewSession).filter_by(id=iid, user_id=user.id).first()
    if not row or row.status != "in_progress":
        raise HTTPException(400, "Interview is not in progress")
    if (getattr(row, "mode", "text") or "text") != "voice":
        raise HTTPException(400, "Not a voice session")
    qs = row.questions or []
    if row.current_index >= len(qs):
        raise HTTPException(400, "No current question")
    audio = synthesize_speech(qs[row.current_index].get("prompt") or "")
    if not audio:
        raise HTTPException(503, "Voice playback is unavailable. Check the LLM key supports TTS, or use the browser speaker.")
    return Response(content=audio, media_type="audio/mpeg")


@router.post("/{iid}/answer")
def answer(iid: int, payload: InterviewAnswerIn, user: CurrentUser, db: DbDep):
    row = db.query(InterviewSession).filter_by(id=iid, user_id=user.id).first()
    if not row or row.status != "in_progress":
        raise HTTPException(400, "Interview is not in progress")
    qs = list(row.questions or [])
    if row.current_index >= len(qs):
        raise HTTPException(400, "No current question")
    profile = ensure_profile(db, user)
    q = dict(qs[row.current_index])
    q["answer"] = payload.answer
    if payload.duration_ms:
        q["voice"] = analyze_speech(payload.answer, payload.duration_ms)
    evaluation = evaluate_answer(
        q,
        payload.answer,
        profile_to_text(user, profile),
        advanced=bool(limits_for(user).get("advanced_analysis")),
        plan=user.plan,
    )
    q["evaluation"] = evaluation
    qs[row.current_index] = q
    qs = apply_followup(qs, row.current_index, evaluation)
    return _finish_answer(row, qs, evaluation, user, db)


@router.post("/{iid}/transcribe")
async def transcribe_voice(
    iid: int,
    user: CurrentUser,
    db: DbDep,
    audio: UploadFile = File(...),
    duration_ms: int = Form(0),
):
    """Turn a recording into text only. Scoring happens when the user submits."""
    row = db.query(InterviewSession).filter_by(id=iid, user_id=user.id).first()
    if not row or row.status != "in_progress":
        raise HTTPException(400, "Interview is not in progress")
    if (getattr(row, "mode", "text") or "text") != "voice":
        raise HTTPException(400, "Not a voice session")
    data = await audio.read()
    text = transcribe_audio(data, audio.filename or "answer.webm")
    if not text:
        raise HTTPException(400, "Could not transcribe the recording. Try again or type the answer.")
    return {"transcript": text, "duration_ms": duration_ms}


@router.post("/{iid}/voice-answer")
async def voice_answer(
    iid: int,
    user: CurrentUser,
    db: DbDep,
    audio: UploadFile = File(...),
    duration_ms: int = Form(0),
    transcript: str = Form(""),
):
    row = db.query(InterviewSession).filter_by(id=iid, user_id=user.id).first()
    if not row or row.status != "in_progress":
        raise HTTPException(400, "Interview is not in progress")
    if (getattr(row, "mode", "text") or "text") != "voice":
        raise HTTPException(400, "Not a voice session")
    qs = list(row.questions or [])
    if row.current_index >= len(qs):
        raise HTTPException(400, "No current question")
    data = await audio.read()
    text = transcribe_audio(data, audio.filename or "answer.webm") or (transcript or "").strip()
    if not text:
        raise HTTPException(400, "Could not transcribe the recording. Try again or type the answer.")
    profile = ensure_profile(db, user)
    q = dict(qs[row.current_index])
    q["answer"] = text
    q["voice"] = analyze_speech(text, duration_ms)
    evaluation = evaluate_answer(
        q,
        text,
        profile_to_text(user, profile),
        advanced=bool(limits_for(user).get("advanced_analysis")),
        plan=user.plan,
    )
    q["evaluation"] = evaluation
    qs[row.current_index] = q
    qs = apply_followup(qs, row.current_index, evaluation)
    return _finish_answer(row, qs, evaluation, user, db)


@router.post("/{iid}/end")
def end_early(iid: int, user: CurrentUser, db: DbDep):
    row = db.query(InterviewSession).filter_by(id=iid, user_id=user.id).first()
    if not row:
        raise HTTPException(404, "Interview not found")
    report = build_report(row.questions or [], row.target_role)
    row.report = report
    row.overall_score = report.get("overall")
    row.status = "completed"
    row.completed_at = datetime.now(timezone.utc)
    db.commit()
    recompute_scores(db, user)
    return _out(row)
