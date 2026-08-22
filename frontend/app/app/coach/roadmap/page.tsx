"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { desiredRole } from "@/lib/role";

type Task = {
  id: string;
  title: string;
  skill: string;
  day?: string;
  objective: string;
  resource: string;
  exercise: string;
  project: string;
  expected_result: string;
  deadline: string;
  completed: boolean;
  kind?: string;
};
type Roadmap = {
  id: number;
  target_role: string;
  duration_months: number;
  duration_label?: string;
  milestones: { month: number; week?: number; title: string; tasks: Task[] }[];
  progress: { done: number; total: number };
};

const PRESETS = ["2-weeks", "1-months", "3-months", "6-months", "12-months"];

function parseDuration(row: Roadmap) {
  const label = (row.duration_label || `${row.duration_months} months`).toLowerCase();
  const match = label.match(/(\d+)\s*(day|days|week|weeks|month|months)/);
  if (!match) {
    return { amount: String(row.duration_months), unit: "months" };
  }
  return {
    amount: match[1],
    unit: match[2].startsWith("day") ? "days" : match[2].startsWith("week") ? "weeks" : "months",
  };
}

export default function RoadmapPage() {
  const [rows, setRows] = useState<Roadmap[]>([]);
  const [active, setActive] = useState<Roadmap | null>(null);
  const [error, setError] = useState("");
  const [topic, setTopic] = useState("");
  const [preset, setPreset] = useState("3-months");
  const [customAmount, setCustomAmount] = useState("3");
  const [customUnit, setCustomUnit] = useState("months");

  function applyForm(row: Roadmap) {
    setTopic(row.target_role || "");
    const dur = parseDuration(row);
    const key = `${dur.amount}-${dur.unit}`;
    setPreset(PRESETS.includes(key) ? key : "custom");
    setCustomAmount(dur.amount);
    setCustomUnit(dur.unit);
  }

  function openRoadmap(row: Roadmap) {
    setActive(row);
    applyForm(row);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function load(preferId?: number) {
    const list = await api<Roadmap[]>("/api/career/roadmap");
    setRows(list);
    const chosen = (preferId && list.find((r) => r.id === preferId)) || list[0];
    if (chosen) {
      setActive(chosen);
      applyForm(chosen);
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    desiredRole().then((role) => {
      setTopic((current) => current || role);
    });
  }, []);

  function durationPayload() {
    return {
      duration_unit: customUnit,
      duration_value: Number(customAmount) || 1,
      duration_months: customUnit === "months" ? Number(customAmount) || 1 : 1,
    };
  }

  function applyPreset(value: string) {
    setPreset(value);
    if (value === "custom") return;
    const [n, unit] = value.split("-");
    setCustomAmount(n);
    setCustomUnit(unit);
  }

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const value = topic.trim();
    if (!value) {
      setError("Enter a skill or career to plan for.");
      return;
    }
    setError("");
    try {
      const row = await api<Roadmap>("/api/career/roadmap", {
        method: "POST",
        body: JSON.stringify({
          focus_skill: value,
          target_role: value,
          ...durationPayload(),
        }),
      });
      setActive(row);
      applyForm(row);
      await load(row.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function patch(milestone_index: number, task_id: string, body: object) {
    if (!active) return;
    const row = await api<Roadmap>(`/api/career/roadmap/${active.id}/tasks`, {
      method: "PATCH",
      body: JSON.stringify({ milestone_index, task_id, ...body }),
    });
    setActive(row);
    applyForm(row);
    setRows((prev) => prev.map((r) => (r.id === row.id ? row : r)));
  }

  return (
    <div>
      <PageTitle kicker="Career coach" title="Learning roadmap" />
      <p className="mb-4 max-w-3xl text-sm text-mist">
        Enter a skill or a career — research writing, CAD, AI Engineer. The plan stays on that topic. Choosing a saved
        plan below fills this form and shows that roadmap.
      </p>
      <Card className="mb-6">
        <form onSubmit={create} className="grid gap-3 md:grid-cols-2">
          <Field label="Skill or career">
            <input
              className={inputClass}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Research writing, AI Engineer, public speaking…"
              required
            />
          </Field>
          <Field label="Duration">
            <select className={inputClass} value={preset} onChange={(e) => applyPreset(e.target.value)}>
              <option value="2-weeks">2 weeks</option>
              <option value="1-months">1 month</option>
              <option value="3-months">3 months</option>
              <option value="6-months">6 months</option>
              <option value="12-months">12 months</option>
              <option value="custom">Custom…</option>
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3 md:col-span-2">
            <Field label="Customize length">
              <input
                className={inputClass}
                type="number"
                min={1}
                max={120}
                value={customAmount}
                onChange={(e) => {
                  setCustomAmount(e.target.value);
                  setPreset("custom");
                }}
              />
            </Field>
            <Field label="Unit">
              <select
                className={inputClass}
                value={customUnit}
                onChange={(e) => {
                  setCustomUnit(e.target.value);
                  setPreset("custom");
                }}
              >
                <option value="days">Days</option>
                <option value="weeks">Weeks</option>
                <option value="months">Months</option>
              </select>
            </Field>
          </div>
          <div className="flex items-end md:col-span-2">
            <Button type="submit">Generate roadmap</Button>
          </div>
        </form>
      </Card>
      <ErrorText error={error} />
      {active && (
        <>
          <p className="mb-4 text-sm text-mist">
            {active.target_role} · {active.duration_label || `${active.duration_months} months`} · {active.progress.done}/
            {active.progress.total} daily tasks
          </p>
          <div className="space-y-4">
            {active.milestones.map((m, mi) => (
              <Card key={`${m.week || m.month}-${mi}`}>
                <h2 className="font-display text-2xl">{m.title}</h2>
                <ul className="mt-4 space-y-3">
                  {m.tasks.map((t) => (
                    <li key={t.id} className="rounded-xl border border-ink/10 p-4">
                      <label className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={t.completed}
                          onChange={(e) => patch(mi, t.id, { completed: e.target.checked, action: "complete" })}
                          className="mt-1"
                        />
                        <div className="flex-1">
                          <div className="font-medium">{t.title}</div>
                          <p className="text-sm text-mist">{t.objective}</p>
                          <p className="mt-2 text-xs text-mist">
                            Resource: {t.resource} · Exercise: {t.exercise} · Project: {t.project}
                          </p>
                          <div className="mt-2 flex gap-2">
                            <input
                              className={`${inputClass} max-w-xs`}
                              defaultValue={t.deadline}
                              onBlur={(e) => patch(mi, t.id, { deadline: e.target.value, action: "deadline" })}
                            />
                            <button className="text-xs text-copper" onClick={() => patch(mi, t.id, { action: "remove" })}>
                              Remove
                            </button>
                          </div>
                        </div>
                      </label>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        </>
      )}
      {rows.length > 0 && (
        <div className="mt-6 text-sm text-mist">
          Saved roadmaps:{" "}
          {rows.map((r) => (
            <button
              key={r.id}
              className={`mr-3 ${active?.id === r.id ? "font-medium text-ink underline" : "text-copper"}`}
              onClick={() => openRoadmap(r)}
            >
              {r.target_role} ({r.duration_label || `${r.duration_months}m`})
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
