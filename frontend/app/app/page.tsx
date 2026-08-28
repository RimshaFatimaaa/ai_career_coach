"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Score } from "@/components/ui";
import { api } from "@/lib/api";

type DueReminder = {
  id: number;
  title: string;
  due_at: string | null;
  overdue: boolean;
};

type Dash = {
  career_goal: string;
  readiness: number;
  resume_health: number;
  interview_performance: number;
  top_skill_gaps: string[];
  roadmap_progress: string | null;
  next_action: string;
  counts: { resumes: number; interviews: number; roadmaps: number };
  due_reminders: DueReminder[];
  profile_complete: boolean;
  disclaimer: string;
};

function dueLabel(due: string | null) {
  if (!due) return "No date";
  return new Date(due).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function DashboardPage() {
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState("");
  const [voiceAllowed, setVoiceAllowed] = useState(false);

  useEffect(() => {
    api<Dash>("/api/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
    api<{ voice_interviews?: boolean }>("/api/billing/usage")
      .then((u) => setVoiceAllowed(Boolean(u.voice_interviews)))
      .catch(() => setVoiceAllowed(false));
  }, []);

  if (!data) {
    return (
      <div>
        <ErrorText error={error} />
        <p className="text-mist">{error ? "Could not load your dashboard." : "Loading your career state…"}</p>
      </div>
    );
  }

  return (
    <div>
      <PageTitle kicker="Overview" title="Where you stand" />
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <div className="text-xs uppercase tracking-[0.16em] text-mist">Career goal</div>
          <div className="mt-2 font-display text-3xl">{data.career_goal}</div>
          <p className="mt-4 text-sm text-mist">{data.next_action}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Button href="/app/coach/skill-gap">Run skill-gap</Button>
            <Button href="/app/resume" variant="ghost">
              Resume studio
            </Button>
            <Button href="/app/interview" variant="ink">
              Start a mock
            </Button>
            {voiceAllowed && (
              <Button href="/app/interview?mode=voice" variant="ghost">
                Start a voice mock
              </Button>
            )}
            <Button href="/app/imports" variant="ghost">
              Import GitHub
            </Button>
          </div>
        </Card>
        <Card>
          <Score value={data.readiness} label="Career readiness" hint={`${Math.round(data.readiness)} / 100 · skill fit + resume + interviews`} />
          <div className="mt-6 space-y-4">
            <Score value={data.resume_health} label="Resume health" hint={`${Math.round(data.resume_health)} / 100 · resume completeness`} />
            <Score value={data.interview_performance} label="Interview performance" hint={`${Math.round(data.interview_performance)} / 100 · average mock`} />
          </div>
          <p className="mt-4 text-xs text-mist">Start at 0. They rise as you build a resume, finish mocks, and follow a roadmap.</p>
        </Card>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Card>
          <div className="text-xs uppercase tracking-[0.16em] text-mist">Top skill gaps</div>
          <ol className="mt-3 space-y-2">
            {(data.top_skill_gaps.length ? data.top_skill_gaps : ["Run a skill-gap analysis to fill this."]).map(
              (g, i) => (
                <li key={g} className="flex gap-3 text-sm">
                  <span className="text-copper">{i + 1}.</span> {g}
                </li>
              )
            )}
          </ol>
        </Card>
        <Card>
          <div className="text-xs uppercase tracking-[0.16em] text-mist">Current roadmap</div>
          <p className="mt-3 font-display text-2xl">{data.roadmap_progress || "Not started"}</p>
          <Link href="/app/coach/roadmap" className="mt-4 inline-block text-sm text-copper">
            Open roadmap →
          </Link>
        </Card>
        <Card>
          <div className="text-xs uppercase tracking-[0.16em] text-mist">Activity</div>
          <p className="mt-3 text-sm">{data.counts.resumes} active resumes</p>
          <p className="text-sm">{data.counts.interviews} mock interviews</p>
          <p className="text-sm">{data.counts.roadmaps} roadmaps</p>
          <Link href="/app/insights" className="mt-4 inline-block text-sm text-copper">
            Career insights →
          </Link>
          {!data.profile_complete && (
            <Link href="/app/profile" className="mt-2 block text-sm text-copper">
              Complete your profile first →
            </Link>
          )}
        </Card>
      </div>
      {data.due_reminders?.length > 0 && (
        <Card className="mt-4">
          <div className="text-xs uppercase tracking-[0.16em] text-mist">Coming up</div>
          <ul className="mt-3 space-y-2">
            {data.due_reminders.map((r) => (
              <li key={r.id} className="flex items-baseline justify-between gap-4 text-sm">
                <span>{r.title}</span>
                <span className={r.overdue ? "shrink-0 text-copper" : "shrink-0 text-mist"}>
                  {r.overdue ? "Overdue" : dueLabel(r.due_at)}
                </span>
              </li>
            ))}
          </ul>
          <Link href="/app/reminders" className="mt-4 inline-block text-sm text-copper">
            All reminders →
          </Link>
        </Card>
      )}
      <p className="mt-6 text-xs text-mist">{data.disclaimer}</p>
    </div>
  );
}
