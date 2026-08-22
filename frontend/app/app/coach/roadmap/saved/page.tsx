"use client";

import { useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";

type Roadmap = {
  id: number;
  target_role: string;
  duration_months: number;
  duration_label?: string;
  progress: { done: number; total: number };
  updated_at?: string;
};

export default function SavedRoadmapsPage() {
  const [rows, setRows] = useState<Roadmap[]>([]);
  const [error, setError] = useState("");

  async function load() {
    const list = await api<Roadmap[]>("/api/career/roadmap?saved=true");
    setRows(list);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function remove(id: number) {
    await api(`/api/career/roadmap/${id}`, { method: "DELETE" });
    setRows((prev) => prev.filter((r) => r.id !== id));
  }

  return (
    <div>
      <PageTitle
        title="Saved roadmaps"
        action={
          <Button href="/app/coach/roadmap" variant="ghost">
            New roadmap
          </Button>
        }
      />
      <p className="mb-6 max-w-2xl text-sm text-mist">
        Plans you saved from the roadmap studio. Open one to keep ticking tasks, or delete it from this list.
      </p>
      <ErrorText error={error} />
      {rows.length === 0 && (
        <Card>
          <p className="text-sm text-mist">No saved roadmaps yet. Generate a plan, then click Save roadmap.</p>
          <Button href="/app/coach/roadmap" className="mt-4">
            Go to roadmap studio
          </Button>
        </Card>
      )}
      <div className="grid gap-3">
        {rows.map((r) => (
          <Card key={r.id} className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-display text-2xl">{r.target_role}</div>
              <p className="mt-1 text-sm text-mist">
                {r.duration_label || `${r.duration_months} month plan`} · {r.progress.done}/{r.progress.total} tasks
                done
              </p>
            </div>
            <div className="flex gap-2">
              <Button href={`/app/coach/roadmap?id=${r.id}`}>Open</Button>
              <Button variant="ghost" onClick={() => remove(r.id)}>
                Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
