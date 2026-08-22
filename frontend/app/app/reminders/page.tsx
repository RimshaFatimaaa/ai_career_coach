"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Reminder = {
  id: number;
  title: string;
  body: string;
  due_at: string | null;
  source: string;
  done: boolean;
  overdue: boolean;
};

export default function RemindersPage() {
  const [rows, setRows] = useState<Reminder[]>([]);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [due, setDue] = useState("");

  async function load() {
    const list = await api<Reminder[]>("/api/reminders");
    setRows(list);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function generate() {
    setError("");
    try {
      const list = await api<Reminder[]>("/api/reminders/generate", { method: "POST" });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate");
    }
  }

  async function add(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/reminders", {
        method: "POST",
        body: JSON.stringify({ title, body, due_at: due ? new Date(due).toISOString() : null }),
      });
      setTitle("");
      setBody("");
      setDue("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add");
    }
  }

  async function toggle(id: number, done: boolean) {
    await api(`/api/reminders/${id}`, { method: "PATCH", body: JSON.stringify({ done }) });
    await load();
  }

  return (
    <div>
      <PageTitle
        kicker="Phase 3"
        title="Reminders"
        action={
          <Button variant="ghost" onClick={generate}>
            Build from roadmap & interviews
          </Button>
        }
      />
      <ErrorText error={error} />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-3">
          {rows.length === 0 && <p className="text-sm text-mist">No open reminders. Generate from your roadmap or add one.</p>}
          {rows.map((r) => (
            <Card key={r.id} className="flex items-start justify-between gap-4">
              <div>
                <p className="font-medium">{r.title}</p>
                {r.body && <p className="mt-1 text-sm text-mist">{r.body}</p>}
                <p className="mt-2 text-xs uppercase tracking-[0.16em] text-mist">
                  {r.source}
                  {r.due_at ? ` · ${new Date(r.due_at).toLocaleDateString()}` : ""}
                  {r.overdue ? " · overdue" : ""}
                </p>
              </div>
              <Button variant="ghost" onClick={() => toggle(r.id, true)}>
                Done
              </Button>
            </Card>
          ))}
        </div>
        <Card>
          <h2 className="font-display text-2xl">New reminder</h2>
          <form className="mt-4 space-y-3" onSubmit={add}>
            <Field label="Title">
              <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} required />
            </Field>
            <Field label="Note">
              <textarea className={inputClass} rows={4} value={body} onChange={(e) => setBody(e.target.value)} />
            </Field>
            <Field label="Due">
              <input className={inputClass} type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />
            </Field>
            <Button type="submit">Save reminder</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
