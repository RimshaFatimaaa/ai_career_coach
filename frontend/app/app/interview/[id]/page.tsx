"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, inputClass } from "@/components/ui";
import { api, getToken } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Interview = {
  id: number;
  target_role: string;
  status: string;
  mode?: string;
  current_question: { prompt: string; type: string; is_followup?: boolean } | null;
  answered: number;
  total: number;
  report: {
    overall?: number;
    technical_knowledge?: number;
    communication?: number;
    answer_structure?: number;
    relevance?: number;
    strengths?: string[];
    weaknesses?: string[];
    recommended_practice?: string[];
    disclaimer?: string;
    voice?: {
      avg_words_per_minute?: number;
      avg_filler_rate?: number;
      avg_clarity?: number;
      speaking_pace?: string;
      avg_pause_ratio?: number;
      avg_word_count?: number;
      disclaimer?: string;
    };
  } | null;
  overall_score: number | null;
};

export default function InterviewSessionPage() {
  const params = useParams<{ id: string }>();
  const [row, setRow] = useState<Interview | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [lastEval, setLastEval] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceDurationMs, setVoiceDurationMs] = useState(0);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedRef = useRef(0);
  const playedKey = useRef("");

  async function load() {
    setRow(await api<Interview>(`/api/interviews/${params.id}`));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [params.id]);

  async function playQuestion(prompt?: string) {
    setError("");
    try {
      const res = await fetch(`${API}/api/interviews/${params.id}/speak`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        await audio.play();
        audio.onended = () => URL.revokeObjectURL(url);
        return;
      }
    } catch {
      /* fall through to browser speech */
    }
    const text = prompt || row?.current_question?.prompt;
    if (text && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
    }
  }

  useEffect(() => {
    if (!row || row.status !== "in_progress" || row.mode !== "voice" || !row.current_question?.prompt) return;
    const key = `${row.id}-${row.answered}-${row.current_question.prompt}`;
    if (playedKey.current === key) return;
    playedKey.current = key;
    void playQuestion(row.current_question.prompt);
  }, [row?.id, row?.answered, row?.mode, row?.current_question?.prompt]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api<Interview & { evaluation: Record<string, unknown> }>(`/api/interviews/${params.id}/answer`, {
        method: "POST",
        body: JSON.stringify({ answer, duration_ms: voiceDurationMs || undefined }),
      });
      setLastEval(res.evaluation);
      setAnswer("");
      setVoiceDurationMs(0);
      setRow(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecord() {
    if (recording) {
      recRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((t) => MediaRecorder.isTypeSupported(t));
      const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (ev) => {
        if (ev.data.size) chunksRef.current.push(ev.data);
      };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        const duration = Date.now() - startedRef.current;
        setVoiceDurationMs(duration);
        setBusy(true);
        setError("");
        try {
          const ext = (rec.mimeType || "").includes("mp4") ? "mp4" : "webm";
          const fd = new FormData();
          fd.append("audio", blob, `answer.${ext}`);
          fd.append("duration_ms", String(duration));
          const res = await api<{ transcript: string }>(`/api/interviews/${params.id}/transcribe`, {
            method: "POST",
            body: fd,
          });
          setAnswer((prev) => (prev.trim() ? `${prev.trim()} ${res.transcript}` : res.transcript));
        } catch (err) {
          setError(err instanceof Error ? err.message : "Could not transcribe. Type your answer, then submit.");
        } finally {
          setBusy(false);
        }
      };
      recRef.current = rec;
      startedRef.current = Date.now();
      rec.start(250);
      setRecording(true);
    } catch {
      setError("Microphone permission is required for voice interviews.");
    }
  }

  if (!row) return <p className="text-mist">Loading session…</p>;

  if (row.status === "completed" && row.report) {
    const r = row.report;
    return (
      <div>
        <PageTitle kicker="Interview report" title={`${row.target_role} · ${r.overall}%`} />
        <p className="mb-6 text-xs text-mist">{r.disclaimer}</p>
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Role knowledge", r.technical_knowledge],
            ["Communication", r.communication],
            ["Structure", r.answer_structure],
            ["Relevance", r.relevance],
          ].map(([k, v]) => (
            <Card key={String(k)}>
              <div className="text-xs text-mist">{String(k)}</div>
              <div className="font-display text-3xl">{v ?? "—"}</div>
            </Card>
          ))}
        </div>
        {r.voice && (
          <Card className="mt-4">
            <h3 className="font-display text-2xl">Voice analytics</h3>
            <p className="mt-1 text-xs text-mist">{r.voice.disclaimer}</p>
            <div className="mt-3 grid gap-3 md:grid-cols-5 text-sm">
              <div>
                <div className="text-xs text-mist">Pace</div>
                <div className="font-display text-2xl">{r.voice.speaking_pace}</div>
                <div className="text-mist">{r.voice.avg_words_per_minute} wpm</div>
              </div>
              <div>
                <div className="text-xs text-mist">Filler rate</div>
                <div className="font-display text-2xl">{r.voice.avg_filler_rate}%</div>
              </div>
              <div>
                <div className="text-xs text-mist">Clarity estimate</div>
                <div className="font-display text-2xl">{r.voice.avg_clarity}</div>
              </div>
              <div>
                <div className="text-xs text-mist">Pause ratio</div>
                <div className="font-display text-2xl">{r.voice.avg_pause_ratio}</div>
              </div>
              <div>
                <div className="text-xs text-mist">Answer length</div>
                <div className="font-display text-2xl">{r.voice.avg_word_count}</div>
                <div className="text-mist">words avg</div>
              </div>
            </div>
          </Card>
        )}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Card>
            <h3 className="font-display text-2xl">Strengths</h3>
            <ul className="mt-3 list-disc pl-5 text-sm">
              {(r.strengths || []).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </Card>
          <Card>
            <h3 className="font-display text-2xl">Weaknesses</h3>
            <ul className="mt-3 list-disc pl-5 text-sm">
              {(r.weaknesses || []).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </Card>
        </div>
        <Card className="mt-4">
          <h3 className="font-display text-2xl">Practice next</h3>
          <ul className="mt-3 list-disc pl-5 text-sm">
            {(r.recommended_practice || []).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </Card>
      </div>
    );
  }

  const voice = row.mode === "voice";

  return (
    <div>
      <PageTitle
        kicker={voice ? "Voice interview" : row.current_question?.is_followup ? "Follow-up" : row.current_question?.type}
        title={`Question ${row.answered + 1} of ${row.total}`}
      />
      <ErrorText error={error} />
      {voice && (
        <p className="mb-3 text-sm text-mist">
          Voice session: the question plays aloud. Record, stop, and the transcript appears in the box below. Edit it if
          needed, then submit to score.
        </p>
      )}
      {row.current_question?.is_followup && (
        <p className="mb-3 text-sm text-mist">
          Follow-up — this replaced the next planned question, so the interview still ends at {row.total}.
        </p>
      )}
      <Card>
        <p className="font-display text-2xl leading-snug">{row.current_question?.prompt}</p>
        {voice && (
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="ghost" onClick={() => playQuestion()}>
              Play question
            </Button>
            <Button variant={recording ? "ink" : "copper"} onClick={toggleRecord} disabled={busy}>
              {recording ? "Stop recording" : busy ? "Transcribing…" : "Record answer"}
            </Button>
          </div>
        )}
        <form onSubmit={submit} className="mt-6 space-y-3">
          <textarea
            className={inputClass}
            rows={8}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder={voice ? "Your recording will appear here. Edit if needed, then submit." : "Answer in STAR if this is behavioral…"}
          />
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || !answer.trim()}>
              {busy ? "Evaluating…" : voice ? "Submit answer" : "Submit typed answer"}
            </Button>
            <Button
              variant="ghost"
              onClick={async () => {
                setError("");
                try {
                  await api(`/api/interviews/${params.id}/end`, { method: "POST" });
                  await load();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Could not end interview");
                }
              }}
            >
              End & report
            </Button>
          </div>
        </form>
      </Card>
      {lastEval && (
        <Card className="mt-4 space-y-2">
          <div className="text-sm">Last score: {String(lastEval.overall ?? "—")}</div>
          {Array.isArray(lastEval.strengths) && lastEval.strengths.length > 0 && (
            <p className="text-sm">Strengths: {(lastEval.strengths as string[]).join(" · ")}</p>
          )}
          {Array.isArray(lastEval.weaknesses) && lastEval.weaknesses.length > 0 && (
            <p className="text-sm text-mist">Work on: {(lastEval.weaknesses as string[]).join(" · ")}</p>
          )}
          {typeof lastEval.improved_example === "string" && lastEval.improved_example && (
            <p className="text-sm text-mist">Stronger version: {lastEval.improved_example}</p>
          )}
        </Card>
      )}
    </div>
  );
}
