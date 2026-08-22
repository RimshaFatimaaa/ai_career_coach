"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { desiredRole } from "@/lib/role";

type Session = {
  id: number;
  target_role: string;
  interview_type: string;
  mode?: string;
  status: string;
  overall_score: number | null;
  created_at: string;
};

export default function InterviewListPage() {
  const [rows, setRows] = useState<Session[]>([]);
  const [error, setError] = useState("");
  const [role, setRole] = useState("");
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [voiceAllowed, setVoiceAllowed] = useState(false);

  async function load() {
    setRows(await api<Session[]>("/api/interviews"));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
    desiredRole().then(setRole);
    api<{ voice_interviews?: boolean }>("/api/billing/usage")
      .then((u) => {
        const allowed = Boolean(u.voice_interviews);
        setVoiceAllowed(allowed);
        const q = new URLSearchParams(window.location.search).get("mode");
        if (q === "voice" && allowed) setMode("voice");
      })
      .catch(() => setVoiceAllowed(false));
  }, []);

  async function start(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setError("");
    try {
      const s = await api<{ id: number }>("/api/interviews/start", {
        method: "POST",
        body: JSON.stringify({
          target_role: fd.get("target_role"),
          interview_type: fd.get("interview_type"),
          job_description: fd.get("job_description"),
          question_count: Number(fd.get("question_count") || 6),
          mode,
        }),
      });
      window.location.href = `/app/interview/${s.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start");
    }
  }

  return (
    <div>
      <PageTitle kicker="Pillar 03" title="Interview coach" />
      <ErrorText error={error} />
      <Card className="mb-6">
        <h2 className="font-display text-2xl">New mock interview</h2>
        <p className="mb-4 mt-1 text-sm text-mist">
          Adaptive: a weak answer gets a follow-up that <em>replaces</em> the next planned question, so a 6-question
          interview stays 6 questions.
        </p>
        <div className="mb-5 grid gap-3 md:grid-cols-2">
          <button
            type="button"
            onClick={() => setMode("text")}
            className={`rounded-2xl border px-4 py-4 text-left transition ${
              mode === "text" ? "border-copper bg-cream" : "border-ink/10 bg-white/70 hover:border-ink/20"
            }`}
          >
            <div className="text-xs uppercase tracking-[0.16em] text-mist">All plans</div>
            <div className="mt-1 font-display text-2xl">Text interview</div>
            <p className="mt-1 text-sm text-mist">Type your answers. STAR scoring and a written report.</p>
          </button>
          <button
            type="button"
            onClick={() => {
              if (voiceAllowed) setMode("voice");
            }}
            className={`rounded-2xl border px-4 py-4 text-left transition ${
              mode === "voice" ? "border-copper bg-cream" : "border-ink/10 bg-white/70"
            } ${voiceAllowed ? "hover:border-ink/20" : "cursor-not-allowed opacity-70"}`}
          >
            <div className="text-xs uppercase tracking-[0.16em] text-mist">Premium</div>
            <div className="mt-1 font-display text-2xl">Voice interview</div>
            <p className="mt-1 text-sm text-mist">
              {voiceAllowed
                ? "Hear the question, record your answer. Pace, fillers, pauses, and length are scored."
                : "Included on Premium. Upgrade in Settings to unlock recording and speaking analytics."}
            </p>
            {!voiceAllowed && (
              <Link href="/app/settings" className="mt-2 inline-block text-sm text-copper">
                Upgrade to Premium →
              </Link>
            )}
          </button>
        </div>
        <form onSubmit={start} className="grid gap-3 md:grid-cols-2">
          <Field label="Target role">
            <input name="target_role" required className={inputClass} defaultValue={role} key={role} placeholder="Architect, Artist, Nurse…" />
          </Field>
          <Field label="Type">
            <select name="interview_type" className={inputClass}>
              <option value="mixed">Mixed</option>
              <option value="behavioral">Behavioral</option>
              <option value="technical">Technical</option>
            </select>
          </Field>
          <Field label="Question count">
            <input name="question_count" type="number" min={3} max={12} defaultValue={6} className={inputClass} />
          </Field>
          <div className="flex items-end text-sm text-mist">
            Selected: {mode === "voice" ? "Voice (Premium)" : "Text"}
          </div>
          <div className="md:col-span-2">
            <Field label="Optional job description">
              <textarea name="job_description" className={inputClass} rows={4} />
            </Field>
          </div>
          <Button type="submit" disabled={mode === "voice" && !voiceAllowed}>
            {mode === "voice" ? "Begin voice interview" : "Begin interview"}
          </Button>
        </form>
      </Card>
      <div className="space-y-2">
        {rows.map((r) => (
          <Link
            key={r.id}
            href={`/app/interview/${r.id}`}
            className="flex items-center justify-between rounded-2xl border border-ink/10 bg-white/70 px-5 py-4"
          >
            <div>
              <div className="font-medium">
                {r.target_role} · {r.interview_type}
                {r.mode === "voice" ? " · Voice" : ""}
              </div>
              <div className="text-xs text-mist">{r.status}</div>
            </div>
            <div className="text-sm">{r.overall_score != null ? `${r.overall_score}%` : "In progress"}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
