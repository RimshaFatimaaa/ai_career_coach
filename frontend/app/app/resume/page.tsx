"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Resume = {
  id: number;
  title: string;
  version_type: string;
  template: string;
  source: string;
  target_role: string;
  updated_at: string;
};

export default function ResumeListPage() {
  const [rows, setRows] = useState<Resume[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([{ id: "ats_classic", name: "ATS Classic" }]);

  async function load() {
    setRows(await api<Resume[]>("/api/resumes"));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
    api<{ id: string; name: string }[]>("/api/resumes/templates")
      .then((t) => {
        if (t?.length) setTemplates(t);
      })
      .catch(() => undefined);
  }, []);

  async function generate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("/api/resumes/generate", {
        method: "POST",
        body: JSON.stringify({
          template: fd.get("template"),
          version_type: fd.get("version_type"),
          target_role: fd.get("target_role"),
          title: fd.get("title"),
        }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(row: Resume) {
    if (!confirm(`Delete “${row.title}”? This frees a slot on your plan.`)) return;
    setError("");
    try {
      await api(`/api/resumes/${row.id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete");
    }
  }

  async function upload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("/api/resumes/upload", { method: "POST", body: fd });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageTitle kicker="Pillar 02" title="Resume studio" />
      <ErrorText error={error} />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="font-display text-2xl">Generate from profile</h2>
            <p className="mb-4 mt-1 text-sm text-mist">Facts come only from your profile. Missing pieces are flagged, never invented. Each template is a distinct professional layout — PDF export matches what you see.</p>
          <form onSubmit={generate} className="space-y-3">
            <Field label="Title">
              <input name="title" className={inputClass} placeholder="Master resume" />
            </Field>
            <Field label="Target role">
              <input name="target_role" className={inputClass} placeholder="Architect, Teacher, AI Engineer…" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Template">
                <select name="template" className={inputClass}>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Version type">
                <select name="version_type" className={inputClass}>
                  <option value="master">Master</option>
                  <option value="technical">Technical</option>
                  <option value="academic">Academic</option>
                  <option value="graduate">Graduate</option>
                  <option value="role_specific">Role-specific</option>
                </select>
              </Field>
            </div>
            <Button type="submit" disabled={busy}>
              Generate
            </Button>
          </form>
        </Card>
        <Card>
          <h2 className="font-display text-2xl">Upload & parse</h2>
          <p className="mb-4 mt-1 text-sm text-mist">PDF or DOCX. On Free, this replaces your one active resume. Review extracted sections — parsers miss layout.</p>
          <form onSubmit={upload} className="space-y-3">
            <input name="file" type="file" accept=".pdf,.docx,.txt,.md" required className="text-sm" />
            <div>
              <Button type="submit" variant="ink" disabled={busy}>
                Upload
              </Button>
            </div>
          </form>
        </Card>
      </div>
      <div className="mt-6 space-y-2">
        {rows.map((r) => (
          <div
            key={r.id}
            className="flex items-center justify-between gap-4 rounded-2xl border border-ink/10 bg-white/70 px-5 py-4 hover:border-copper/40"
          >
            <Link href={`/app/resume/${r.id}`} className="min-w-0 flex-1">
              <div className="font-medium">{r.title}</div>
              <div className="text-xs text-mist">
                {r.version_type} · {r.template} · {r.source}
                {r.target_role ? ` · ${r.target_role}` : ""}
              </div>
            </Link>
            <div className="flex shrink-0 items-center gap-3">
              <Link href={`/app/resume/${r.id}`} className="text-sm text-copper">
                Open →
              </Link>
              <button
                type="button"
                className="text-sm text-mist hover:text-copper"
                onClick={() => remove(r)}
                aria-label={`Delete ${r.title}`}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
        {rows.length === 0 && <p className="text-sm text-mist">No resumes yet. Generate from your profile or upload one.</p>}
      </div>
    </div>
  );
}
