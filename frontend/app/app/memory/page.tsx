"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Mem = { id: number; category: string; key: string; value: string; enabled: boolean };

export default function MemoryPage() {
  const [rows, setRows] = useState<Mem[]>([]);
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false);

  async function load() {
    try {
      setRows(await api<Mem[]>("/api/memory"));
      setLocked(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not load career memory";
      if (/Pro and Premium|paid plan/i.test(msg)) {
        setLocked(true);
        setRows([]);
        return;
      }
      throw err;
    }
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setError("");
    try {
      await api("/api/memory", {
        method: "POST",
        body: JSON.stringify({
          category: fd.get("category"),
          key: fd.get("key"),
          value: fd.get("value"),
        }),
      });
      e.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pro plan required for career memory");
    }
  }

  return (
    <div>
      <PageTitle kicker="Memory" title="Career memory" />
      <div className="mb-6 max-w-2xl space-y-3 text-sm text-mist">
        <p>
          Career memory is the coach&apos;s long-term notes about <em>you</em> — preferences that should still be true next
          month. It is not a second profile and not a chat transcript.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong className="text-ink">Career profile</strong> holds facts: degrees, jobs, skills, target role.
          </li>
          <li>
            <strong className="text-ink">A conversation</strong> is one coaching thread. When you start a new chat, that
            thread stays behind.
          </li>
          <li>
            <strong className="text-ink">Career memory</strong> keeps durable preferences across sessions: &quot;I want
            studio practice, not software,&quot; &quot;avoid dense academic CVs,&quot; &quot;STAR structure is my weak
            spot.&quot; The coach reads enabled memories so you do not re-explain yourself.
          </li>
        </ul>
        <p>Pro and Premium can save memories. You can correct, disable, or delete anything stored here.</p>
      </div>
      <ErrorText error={error} />
      {locked && (
        <Card className="mb-6 space-y-3">
          <h2 className="font-display text-2xl">Career memory is on Pro</h2>
          <p className="text-sm text-mist">
            Free accounts do not store durable preferences, and the coach does not read them. Upgrade to keep notes the
            coach carries between conversations. Anything you saved on a paid plan is retained and returns if you
            upgrade again.
          </p>
          <Button href="/app/settings">See plans</Button>
        </Card>
      )}
      <Card className={locked ? "mb-6 opacity-50" : "mb-6"}>
        <form onSubmit={add} className="grid gap-3 md:grid-cols-4">
          <Field label="Category">
            <select name="category" className={inputClass}>
              <option>direction</option>
              <option>learning</option>
              <option>resume</option>
              <option>interview</option>
              <option>decision</option>
            </select>
          </Field>
          <Field label="Key">
            <input name="key" required className={inputClass} placeholder="prefers-studio-practice" />
          </Field>
          <Field label="Value">
            <input name="value" required className={inputClass} placeholder="Target architecture studios, not product companies" />
          </Field>
          <div className="flex items-end">
            <Button type="submit" disabled={locked}>
              Save
            </Button>
          </div>
        </form>
      </Card>
      <div className="space-y-2">
        {rows.map((m) => (
          <Card key={m.id} className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-wider text-mist">{m.category}</div>
              <div className="font-medium">{m.key}</div>
              <p className="text-sm text-mist">{m.value}</p>
              {!m.enabled && <p className="text-xs text-mist">Disabled — the coach will ignore this.</p>}
            </div>
            <div className="flex gap-2 text-xs">
              <button
                className="text-copper"
                onClick={async () => {
                  setError("");
                  try {
                    await api(`/api/memory/${m.id}`, {
                      method: "PATCH",
                      body: JSON.stringify({ enabled: !m.enabled }),
                    });
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Could not update that memory");
                  }
                }}
              >
                {m.enabled ? "Disable" : "Enable"}
              </button>
              <button
                className="text-red-800"
                onClick={async () => {
                  setError("");
                  try {
                    await api(`/api/memory/${m.id}`, { method: "DELETE" });
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Could not delete that memory");
                  }
                }}
              >
                Delete
              </button>
            </div>
          </Card>
        ))}
        {rows.length === 0 && !locked && (
          <p className="text-sm text-mist">Nothing stored yet. Save a preference, or talk to the coach and it can offer to remember one.</p>
        )}
      </div>
    </div>
  );
}
