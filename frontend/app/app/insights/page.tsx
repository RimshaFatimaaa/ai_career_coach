"use client";

import { useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Score } from "@/components/ui";
import { api } from "@/lib/api";

type Analytics = {
  readiness: number;
  resume_health: number;
  interview_performance: number;
  interview_history: { id: number; date: string; role: string; mode: string; score: number; type: string }[];
  interview_trend: string | null;
  interview_count: number;
  avg_interview: number;
  best_interview: number;
  top_strengths: { label: string; count: number }[];
  top_weaknesses: { label: string; count: number }[];
  ats_history: { resume_id: number; title: string; ats_readiness: number }[];
  skill_gap_mix: Record<string, number>;
  roadmap_progress: { done: number; total: number };
  voice: { avg_wpm: number; avg_filler_rate: number; sessions: number } | null;
  disclaimer: string;
};

function Bar({ value, max = 100, color = "#c46b3a" }: { value: number; max?: number; color?: string }) {
  const w = Math.max(4, Math.min(100, (value / (max || 1)) * 100));
  return (
    <div className="h-2 overflow-hidden rounded-full bg-ink/10">
      <div className="h-full rounded-full" style={{ width: `${w}%`, background: color }} />
    </div>
  );
}

export default function InsightsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Analytics>("/api/analytics")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (!data) {
    return (
      <div>
        <ErrorText error={error} />
        <p className="text-mist">{error ? "Could not load insights." : "Building your career analytics…"}</p>
      </div>
    );
  }

  const mixTotal = Object.values(data.skill_gap_mix || {}).reduce((a, b) => a + b, 0) || 1;

  return (
    <div>
      <PageTitle kicker="Phase 3" title="Career insights" />
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <Score value={data.readiness} label="Career readiness" />
        </Card>
        <Card>
          <Score value={data.resume_health} label="Resume health" />
        </Card>
        <Card>
          <Score value={data.interview_performance} label="Interview performance" />
        </Card>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Card>
          <div className="flex items-end justify-between">
            <h2 className="font-display text-2xl">Interview trend</h2>
            <span className="text-xs uppercase tracking-[0.16em] text-mist">
              {data.interview_trend || "need two mocks"} · avg {data.avg_interview} · best {data.best_interview}
            </span>
          </div>
          {data.interview_history.length === 0 ? (
            <p className="mt-4 text-sm text-mist">Finish a mock interview to plot scores over time.</p>
          ) : (
            <div className="mt-4 flex h-40 items-end gap-2">
              {data.interview_history.map((h) => (
                <div key={h.id} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t bg-copper" style={{ height: `${Math.max(8, h.score)}%` }} title={`${h.role} ${h.score}`} />
                  <span className="truncate text-[10px] text-mist">{Math.round(h.score)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <h2 className="font-display text-2xl">Skill-gap mix</h2>
          <div className="mt-4 space-y-3">
            {Object.entries(data.skill_gap_mix).map(([k, v]) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-xs text-mist">
                  <span className="capitalize">{k}</span>
                  <span>{v}</span>
                </div>
                <Bar value={v} max={mixTotal} color={k === "high" ? "#8a3a22" : k === "medium" ? "#c46b3a" : "#245c48"} />
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-mist">
            Roadmap {data.roadmap_progress.done}/{data.roadmap_progress.total} tasks complete
          </p>
        </Card>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="font-display text-2xl">Strengths</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(data.top_strengths.length ? data.top_strengths : [{ label: "Complete mocks to surface patterns.", count: 0 }]).map((s) => (
              <li key={s.label} className="flex justify-between gap-3">
                <span>{s.label}</span>
                {s.count > 0 && <span className="text-mist">{s.count}×</span>}
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="font-display text-2xl">Practice focus</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(data.top_weaknesses.length ? data.top_weaknesses : [{ label: "No recurring gaps yet.", count: 0 }]).map((s) => (
              <li key={s.label} className="flex justify-between gap-3">
                <span>{s.label}</span>
                {s.count > 0 && <span className="text-mist">{s.count}×</span>}
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="font-display text-2xl">ATS history</h2>
          {data.ats_history.length === 0 ? (
            <p className="mt-3 text-sm text-mist">Run ATS analysis against a job description to track resume fit.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {data.ats_history.map((r) => (
                <li key={r.resume_id}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span>{r.title}</span>
                    <span>{r.ats_readiness}%</span>
                  </div>
                  <Bar value={Number(r.ats_readiness || 0)} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <h2 className="font-display text-2xl">Voice analytics</h2>
          {data.voice ? (
            <div className="mt-3 space-y-2 text-sm">
              <p>{data.voice.sessions} voice sessions</p>
              <p>Average pace {data.voice.avg_wpm} words/min</p>
              <p>Filler rate {data.voice.avg_filler_rate}</p>
            </div>
          ) : (
            <p className="mt-3 text-sm text-mist">Premium voice mocks add pace, fillers, and pause stats here.</p>
          )}
          <Button href="/app/interview" className="mt-4" variant="ghost">
            Practice again
          </Button>
        </Card>
      </div>
      <p className="mt-6 text-xs text-mist">{data.disclaimer}</p>
    </div>
  );
}
