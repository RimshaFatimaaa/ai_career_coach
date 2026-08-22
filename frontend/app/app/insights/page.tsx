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
          <Score
            value={data.readiness}
            label="Career readiness"
            hint={`${Math.round(data.readiness)} / 100 · skill fit + resume + interviews`}
          />
        </Card>
        <Card>
          <Score
            value={data.resume_health}
            label="Resume health"
            hint={`${Math.round(data.resume_health)} / 100 · how complete your resumes are`}
          />
        </Card>
        <Card>
          <Score
            value={data.interview_performance}
            label="Interview performance"
            hint={`${Math.round(data.interview_performance)} / 100 · average mock score`}
          />
        </Card>
      </div>
      <div className="mt-4">
        <Card>
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="font-display text-2xl">Interview trend</h2>
              <p className="mt-1 text-xs text-mist">Each bar is that mock’s overall score out of 100.</p>
            </div>
            <span className="text-xs text-mist">
              {data.interview_history.length < 2
                ? "Need 2 mocks to show up/down"
                : `Trend ${data.interview_trend} · avg ${data.avg_interview}/100 · best ${data.best_interview}/100`}
            </span>
          </div>
          {data.interview_history.length === 0 ? (
            <p className="mt-3 text-sm text-mist">Finish a mock interview to plot scores over time.</p>
          ) : (
            <div className="mt-4 flex h-52 gap-3">
              <div className="flex h-[calc(100%-2.5rem)] flex-col justify-between pt-5 text-[10px] text-mist">
                <span>100%</span>
                <span>50%</span>
                <span>0%</span>
              </div>
              <div className="flex min-w-0 flex-1 items-end gap-2">
                {data.interview_history.map((h, i) => {
                  const pct = Math.max(3, Math.min(100, h.score));
                  const name = h.role?.trim() || h.type || "Interview";
                  return (
                    <div key={h.id} className="flex h-full min-w-0 flex-1 flex-col items-center">
                      <div className="relative flex min-h-0 w-full flex-1 items-end rounded-t-lg bg-[#ece3fb] pt-6">
                        <div className="relative w-full rounded-t-lg bg-[#a78bfa]" style={{ height: `${pct}%` }}>
                          <span className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-full text-xs font-medium whitespace-nowrap text-[#3d3453]">
                            {Math.round(h.score)}%
                          </span>
                        </div>
                      </div>
                      <p className="mt-2 w-full truncate text-center text-[11px] leading-snug text-mist" title={`${i + 1}. ${name}`}>
                        {i + 1}. {name}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </Card>
      </div>
      <div className="mt-4">
        <Card>
          <h2 className="font-display text-2xl">Skill-gap mix</h2>
          <p className="mt-1 text-xs text-mist">How many skills from your last roadmap sit in each gap band.</p>
          <div className="mt-3 space-y-2">
            {Object.entries(data.skill_gap_mix)
              .filter(([, v]) => v > 0)
              .map(([k, v]) => (
                <div key={k}>
                  <div className="mb-1 flex justify-between text-xs text-mist">
                    <span className="capitalize">
                      {k === "high" ? "Focus next" : k === "medium" ? "Build next" : k === "low" ? "On track" : "Covered"} · {v} skill{v === 1 ? "" : "s"}
                    </span>
                    <span>
                      {v}/{mixTotal}
                    </span>
                  </div>
                  <Bar value={v} max={mixTotal} color={k === "high" ? "#7c5fc4" : k === "medium" ? "#a78bfa" : "#a7e3d0"} />
                </div>
              ))}
          </div>
          <p className="mt-3 text-sm text-mist">
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
