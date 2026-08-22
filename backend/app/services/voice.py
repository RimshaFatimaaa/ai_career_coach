"""Voice transcription, TTS, and speaking analytics (PRD Phase 2)."""

from __future__ import annotations

import io
import re
from typing import Any

from app.services.llm import gateway

FILLERS = (
    "um",
    "uh",
    "er",
    "ah",
    "like",
    "you know",
    "so",
    "basically",
    "actually",
    "kind of",
    "sort of",
)


def analyze_speech(transcript: str, duration_ms: int) -> dict[str, Any]:
    text = (transcript or "").strip()
    words = [w for w in re.findall(r"[A-Za-z']+", text.lower()) if w]
    duration_s = max((duration_ms or 0) / 1000.0, 0.4)
    wpm = round(len(words) / duration_s * 60, 1) if words else 0.0
    blob = f" {text.lower()} "
    filler_count = 0
    for f in FILLERS:
        filler_count += blob.count(f" {f} ")
    filler_rate = round(100 * filler_count / max(len(words), 1), 1)
    expected_s = max(len(words) / 2.4, 0.4)
    pause_ratio = round(max(0.0, duration_s - expected_s) / duration_s, 2)
    if wpm > 185:
        pace = "fast"
        pace_note = "Slow down slightly so structure is easier to hear."
    elif wpm < 90 and words:
        pace = "slow"
        pace_note = "Pick up the pace a little; long gaps read as uncertainty."
    else:
        pace = "steady"
        pace_note = "Pace is in a natural coaching range."
    clarity = max(20, min(95, 88 - filler_rate * 1.4 - (12 if pause_ratio > 0.45 else 0)))
    return {
        "duration_ms": duration_ms,
        "word_count": len(words),
        "words_per_minute": wpm,
        "filler_count": filler_count,
        "filler_rate": filler_rate,
        "pause_ratio": pause_ratio,
        "speaking_pace": pace,
        "pace_note": pace_note,
        "clarity_estimate": round(clarity, 1),
        "disclaimer": "Voice metrics are coaching estimates from the recording, not a personality assessment.",
    }


def transcribe_audio(data: bytes, filename: str = "answer.webm") -> str:
    client, _ = gateway.openai_audio_client()
    if not client or not data:
        return ""
    buf = io.BytesIO(data)
    buf.name = filename
    try:
        result = client.audio.transcriptions.create(model="whisper-1", file=buf)
        return (getattr(result, "text", None) or str(result) or "").strip()
    except Exception:
        try:
            buf.seek(0)
            result = client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=buf)
            return (getattr(result, "text", None) or "").strip()
        except Exception:
            return ""


def synthesize_speech(text: str) -> bytes:
    client, _ = gateway.openai_audio_client()
    if not client or not text.strip():
        return b""
    try:
        speech = client.audio.speech.create(model="gpt-4o-mini-tts", voice="alloy", input=text[:4000])
        return speech.read() if hasattr(speech, "read") else bytes(speech)
    except Exception:
        try:
            speech = client.audio.speech.create(model="tts-1", voice="alloy", input=text[:4000])
            return speech.read() if hasattr(speech, "read") else bytes(speech)
        except Exception:
            return b""


def aggregate_voice(questions: list[dict]) -> dict[str, Any] | None:
    metrics = [q.get("voice") for q in questions if isinstance(q.get("voice"), dict)]
    if not metrics:
        return None
    n = len(metrics)
    avg = lambda key: round(sum(float(m.get(key) or 0) for m in metrics) / n, 1)
    paces = [m.get("speaking_pace") for m in metrics]
    dominant = max(set(paces), key=paces.count) if paces else "steady"
    return {
        "answers_scored": n,
        "avg_words_per_minute": avg("words_per_minute"),
        "avg_filler_rate": avg("filler_rate"),
        "avg_clarity": avg("clarity_estimate"),
        "avg_pause_ratio": avg("pause_ratio"),
        "avg_word_count": avg("word_count"),
        "speaking_pace": dominant,
        "notes": [
            "Filler-word rate is a coaching signal, not a hiring score.",
            "Pauses are inferred from recording length vs. word count.",
        ],
        "disclaimer": "Voice analytics are AI-generated estimates for practice, not a psychological assessment.",
    }
