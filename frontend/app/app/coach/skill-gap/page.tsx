"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { desiredRole } from "@/lib/role";

type Gap = {
  skill: string;
  current: string;
  target: string;
  gap: string;
  priority_label?: string;
  why_it_matters: string;
  resource: string;
  exercise: string;
  project: string;
  recommended_proficiency: string;
};

type RoleFit = {
  name: string;
  description?: string;
  readiness: number;
  gaps: Gap[];
};

type FitBreakdown = {
  percent: number;
  required_count: number;
  on_track: string[];
  stretch: string[];
  focus: string[];
  formula: string;
};

type Result = {
  readiness?: number;
  gaps?: Gap[];
  recommendation?: string;
  fit_meaning?: string;
  fit?: FitBreakdown;
  fit_a?: FitBreakdown;
  fit_b?: FitBreakdown;
  role_label?: string;
  role_a?: RoleFit;
  role_b?: RoleFit;
  closer?: string | null;
  disclaimer?: string;
};

function gapLabel(g: Gap) {
  if (g.priority_label) return g.priority_label;
  if (g.gap === "high") return "Focus next";
  if (g.gap === "medium") return "Stretch";
  return "On track";
}

function gapClass(g: Gap) {
  const label = gapLabel(g);
  if (label === "Focus next") return "font-medium text-copper";
  if (label === "Stretch") return "font-medium text-[#9a6b2f]";
  if (label === "On track" || label === "On your profile") return "font-medium text-moss";
  return "text-mist";
}

function GapTable({ gaps }: { gaps: Gap[] }) {
  if (!gaps.length) return null;
  return (
    <div className="overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase tracking-wider text-mist">
          <tr>
            {["Skill", "Your level", "Role wants", "Learning priority", "Why", "Resource"].map((h) => (
              <th key={h} className="px-4 py-3 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {gaps.map((g) => (
            <tr key={g.skill} className="border-t border-ink/5 align-top">
              <td className="px-4 py-3 font-medium">{g.skill}</td>
              <td className="px-4 py-3">{g.current}</td>
              <td className="px-4 py-3">{g.target}</td>
              <td className={`px-4 py-3 ${gapClass(g)}`}>{gapLabel(g)}</td>
              <td className="px-4 py-3 text-mist">{g.why_it_matters}</td>
              <td className="px-4 py-3 text-mist">{g.resource}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FitCard({ title, percent, description, breakdown }: { title: string; percent: number; description?: string; breakdown?: FitBreakdown }) {
  return (
    <Card>
      <div className="text-xs uppercase tracking-[0.16em] text-mist">{title}</div>
      <div className="mt-1 font-display text-4xl">{percent}%</div>
      {description && <p className="mt-2 text-sm text-mist">{description}</p>}
      {breakdown && (
        <div className="mt-3 space-y-1 text-xs text-mist">
          {breakdown.on_track.length > 0 && (
            <p>
              <span className="font-medium text-moss">Already counting:</span> {breakdown.on_track.join(", ")}
            </p>
          )}
          {breakdown.focus.length > 0 && (
            <p>
              <span className="font-medium text-copper">Pulling the % down:</span> {breakdown.focus.join(", ")}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

export default function SkillGapPage() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<Result | null>(null);
  const [role, setRole] = useState("");

  useEffect(() => {
    desiredRole().then(setRole);
  }, []);

  async function run(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      const res = await api("/api/career/skill-gap", {
        method: "POST",
        body: JSON.stringify({
          target_role: fd.get("target_role"),
          compare_role: fd.get("compare_role") || null,
        }),
      });
      setData(res as Result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  const comparing = Boolean(data?.role_a && data?.role_b);

  return (
    <div>
      <PageTitle kicker="Career coach" title="Skill-gap analysis" />
      <p className="mb-4 max-w-3xl text-sm text-mist">
        The percentage is not a hiring score. It is the average of{" "}
        <strong className="font-medium text-ink">your level ÷ the role&apos;s required level</strong> across every
        required skill. Missing = 0, Beginner = 1, Intermediate = 2, Strong = 3. Skills you already listed (SQL,
        LangChain, FastAPI, Git, and so on) raise the number. Skills still missing (for AI Engineer that is often
        PyTorch, deep learning, or vector databases) pull it down.
      </p>
      <p className="mb-6 max-w-3xl text-sm text-mist">
        In the table, <strong className="font-medium text-moss">On track</strong> means you already meet that skill.
        Skills and courses from your profile that the role catalog does not list still appear as{" "}
        <strong className="font-medium text-moss">On your profile</strong>.
      </p>
      <Card className="mb-6">
        <form onSubmit={run} className="grid gap-3 md:grid-cols-3">
          <Field label="Target role">
            <input name="target_role" required className={inputClass} defaultValue={role} key={role} placeholder="Architect, Artist, Nurse…" />
          </Field>
          <Field label="Compare with (optional)">
            <input name="compare_role" className={inputClass} placeholder="A second career to weigh" />
          </Field>
          <div className="flex items-end">
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "Analyzing…" : "Analyze"}
            </Button>
          </div>
        </form>
      </Card>
      <ErrorText error={error} />
      {data?.fit_meaning && <p className="mb-4 text-sm text-mist">{data.fit_meaning}</p>}
      {comparing ? (
        <>
          <div className="mb-4 grid gap-4 md:grid-cols-2">
            <FitCard
              title={data!.role_a!.name}
              percent={data!.role_a!.readiness}
              description={data!.role_a!.description}
              breakdown={data?.fit_a}
            />
            <FitCard
              title={data!.role_b!.name}
              percent={data!.role_b!.readiness}
              description={data!.role_b!.description}
              breakdown={data?.fit_b}
            />
          </div>
          {data?.recommendation && <p className="mb-4 text-sm">{data.recommendation}</p>}
          <div className="space-y-6">
            <div>
              <h3 className="mb-2 font-display text-2xl">{data!.role_a!.name}</h3>
              <GapTable gaps={data!.role_a!.gaps || []} />
            </div>
            <div>
              <h3 className="mb-2 font-display text-2xl">{data!.role_b!.name}</h3>
              <GapTable gaps={data!.role_b!.gaps || []} />
            </div>
          </div>
        </>
      ) : (
        <>
          {data?.readiness != null && (
            <FitCard
              title={data.role_label || "this role"}
              percent={data.readiness}
              breakdown={data.fit}
            />
          )}
          {data?.recommendation && <p className="mb-4 mt-4 text-sm">{String(data.recommendation)}</p>}
          <div className="mt-6">
            <GapTable gaps={data?.gaps || []} />
          </div>
        </>
      )}
      {data?.disclaimer && <p className="mt-4 text-xs text-mist">{data.disclaimer}</p>}
    </div>
  );
}
