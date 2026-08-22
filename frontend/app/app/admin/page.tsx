"use client";

import { useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, PasswordInput } from "@/components/ui";
import { api } from "@/lib/api";

export default function AdminPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [users, setUsers] = useState<{ id: number; email: string; plan: string; full_name: string }[]>([]);
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    Promise.all([api<Record<string, unknown>>("/api/admin/overview"), api<typeof users>("/api/admin/users")])
      .then(([o, u]) => {
        setData(o);
        setUsers(u);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <PageTitle kicker="Admin" title="Platform overview" />
      <ErrorText error={error} />
      <p className="mb-6 text-sm text-mist">Admins do not automatically receive private resume files.</p>
      {data && (
        <div className="grid gap-4 md:grid-cols-4">
          {["users", "interviews", "knowledge_chunks", "recorded_tokens"].map((k) => (
            <Card key={k}>
              <div className="text-xs text-mist">{k.replace(/_/g, " ")}</div>
              <div className="font-display text-3xl">{String(data[k])}</div>
            </Card>
          ))}
        </div>
      )}
      <Card className="mt-4">
        <h2 className="font-display text-2xl">Users</h2>
        <p className="mt-1 text-sm text-mist">Assigning a plan requires your admin password — not a silent click.</p>
        <Field label="Admin password">
          <PasswordInput className="mt-2 max-w-sm" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <ul className="mt-3 space-y-2 text-sm">
          {users.map((u) => (
            <li key={u.email} className="flex flex-wrap items-center justify-between gap-2">
              <span>
                {u.full_name} · {u.email}
              </span>
              <span className="flex items-center gap-2">
                <span className="capitalize text-mist">{u.plan}</span>
                {["free", "pro", "premium"].map((p) => (
                  <Button
                    key={p}
                    variant="ghost"
                    className="!px-3 !py-1 text-xs"
                    onClick={async () => {
                      try {
                        const updated = await api<{ plan: string }>(`/api/admin/users/${u.id}/plan`, {
                          method: "POST",
                          body: JSON.stringify({ plan: p, password }),
                        });
                        setUsers(users.map((x) => (x.id === u.id ? { ...x, plan: updated.plan } : x)));
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Could not assign plan");
                      }
                    }}
                  >
                    {p}
                  </Button>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
