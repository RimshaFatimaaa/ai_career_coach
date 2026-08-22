"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Analysis = {
  summary?: string;
  suggested_skills?: string[];
  suggested_projects?: { name: string; description?: string; url?: string }[];
  suggested_experience?: { title?: string; company?: string; notes?: string }[];
  gaps_vs_profile?: string[];
  notes?: string[];
};

type ImportRow = {
  id: number;
  source: string;
  handle: string;
  analysis: Analysis;
  applied: boolean;
  created_at: string;
};

function AnalysisPanel({ row, onApply }: { row: ImportRow; onApply: (id: number) => void }) {
  const analysis = row.analysis || {};
  return (
    <div className="mt-5 space-y-3 border-t border-line/70 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-display text-lg">{row.handle}</h3>
        <Button onClick={() => onApply(row.id)} disabled={row.applied}>
          {row.applied ? "Already applied" : "Add skills & projects to profile"}
        </Button>
      </div>
      {analysis.summary && <p className="text-sm">{analysis.summary}</p>}
      {!!analysis.suggested_skills?.length && (
        <p className="text-sm">
          <span className="text-mist">Skills: </span>
          {analysis.suggested_skills.join(" · ")}
        </p>
      )}
      {!!analysis.suggested_experience?.length && (
        <ul className="list-disc pl-5 text-sm">
          {analysis.suggested_experience.map((job, i) => (
            <li key={`${job.company}-${job.title}-${i}`}>
              {[job.title, job.company].filter(Boolean).join(" · ")}
              {job.notes ? ` — ${job.notes}` : ""}
            </li>
          ))}
        </ul>
      )}
      {!!analysis.suggested_projects?.length && (
        <ul className="list-disc pl-5 text-sm">
          {analysis.suggested_projects.map((p) => (
            <li key={p.name}>
              {p.name}
              {p.description ? ` — ${p.description}` : ""}
            </li>
          ))}
        </ul>
      )}
      {!!analysis.gaps_vs_profile?.length && (
        <p className="text-sm text-mist">Gaps vs profile: {analysis.gaps_vs_profile.join(" · ")}</p>
      )}
    </div>
  );
}

export default function ImportsPage() {
  const [handle, setHandle] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [rows, setRows] = useState<ImportRow[]>([]);

  async function load() {
    const list = await api<ImportRow[]>("/api/imports");
    setRows(list);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function github(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy("github");
    try {
      await api<ImportRow>("/api/imports/github", { method: "POST", body: JSON.stringify({ handle }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "GitHub import failed");
    } finally {
      setBusy("");
    }
  }

  async function linkedinImport(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy("linkedin");
    try {
      await api<ImportRow>("/api/imports/linkedin", {
        method: "POST",
        body: JSON.stringify({ text: linkedin, url }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "LinkedIn analysis failed");
    } finally {
      setBusy("");
    }
  }

  async function apply(id: number) {
    setError("");
    try {
      await api(`/api/imports/${id}/apply`, { method: "POST", body: JSON.stringify({ skills: true, projects: true }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply");
    }
  }

  const githubRow = rows.find((r) => r.source === "github");
  const linkedinRow = rows.find((r) => r.source === "linkedin");

  return (
    <div>
      <PageTitle kicker="Phase 3" title="LinkedIn & GitHub" />
      <ErrorText error={error} />
      <p className="mb-6 max-w-2xl text-sm text-mist">
        We only use public GitHub data, or LinkedIn text you paste. Suggestions are facts to review — they are not added as jobs unless you apply them.
      </p>
      <div className="grid items-start gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="font-display text-2xl">GitHub</h2>
          <form className="mt-4 space-y-3" onSubmit={github}>
            <Field label="Username or profile URL">
              <input className={inputClass} value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="octocat or https://github.com/octocat" />
            </Field>
            <Button type="submit" disabled={!handle || busy === "github"}>
              {busy === "github" ? "Reading public profile…" : "Analyze GitHub"}
            </Button>
          </form>
          {githubRow && <AnalysisPanel row={githubRow} onApply={apply} />}
        </Card>
        <Card>
          <h2 className="font-display text-2xl">LinkedIn</h2>
          <form className="mt-4 space-y-3" onSubmit={linkedinImport}>
            <Field label="Profile URL (optional, not scraped)">
              <input className={inputClass} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.linkedin.com/in/…" />
            </Field>
            <Field label="Paste About + Experience">
              <textarea className={inputClass} rows={8} value={linkedin} onChange={(e) => setLinkedin(e.target.value)} placeholder="Paste the text from your public LinkedIn sections." />
            </Field>
            <Button type="submit" disabled={linkedin.trim().length < 40 || busy === "linkedin"}>
              {busy === "linkedin" ? "Extracting facts…" : "Analyze pasted profile"}
            </Button>
            {linkedin.trim().length < 40 && (
              <p className="text-xs text-mist">
                The URL is not scraped. Paste at least 40 characters from About and Experience — the button stays off until then.
              </p>
            )}
          </form>
          {linkedinRow && <AnalysisPanel row={linkedinRow} onApply={apply} />}
        </Card>
      </div>
    </div>
  );
}
