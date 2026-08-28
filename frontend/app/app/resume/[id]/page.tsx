"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { ResumePaper } from "@/components/ResumePaper";
import { api, downloadFile } from "@/lib/api";

type Content = {
  contact?: Record<string, string>;
  summary?: string;
  skills?: Record<string, string[]>;
  experience?: Record<string, unknown>[];
  education?: Record<string, unknown>[];
  projects?: Record<string, unknown>[];
  flagged_missing?: string[];
};

type Resume = {
  id: number;
  title: string;
  template: string;
  version_type: string;
  content: Content;
  change_log: string[];
  last_ats: Record<string, unknown> | null;
  target_role: string;
};

function isBlank(value: unknown): boolean {
  if (value == null) return true;
  if (typeof value === "string") {
    return ["", "nothing", "n/a", "na", "-", "none"].includes(value.trim().toLowerCase());
  }
  if (Array.isArray(value)) return value.every(isBlank);
  if (typeof value === "object") return Object.values(value as object).every(isBlank);
  return false;
}

function bullets(item: Record<string, unknown>) {
  const a = Array.isArray(item.responsibilities) ? item.responsibilities : [];
  const b = Array.isArray(item.achievements) ? item.achievements : [];
  return [...a, ...b].map(String).filter((x) => !isBlank(x));
}

export default function ResumeDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [row, setRow] = useState<Resume | null>(null);
  const [content, setContent] = useState<Content>({});
  const [jd, setJd] = useState("");
  const [error, setError] = useState("");
  const [ats, setAts] = useState<Record<string, unknown> | null>(null);
  const [letter, setLetter] = useState("");
  const [letterFlags, setLetterFlags] = useState<string[]>([]);
  const [style, setStyle] = useState("professional");
  const [template, setTemplate] = useState("ats_classic");
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([{ id: "ats_classic", name: "ATS Classic" }]);
  const [editing, setEditing] = useState(false);
  const [docxAllowed, setDocxAllowed] = useState(false);

  async function load() {
    const r = await api<Resume>(`/api/resumes/${params.id}`);
    setRow(r);
    const c = r.content || {};
    if (isBlank(c.summary)) c.summary = "";
    setContent(c);
    setAts(r.last_ats);
    setTemplate(r.template);
  }
  useEffect(() => {
    setRow(null);
    setJd("");
    setLetter("");
    setLetterFlags([]);
    setAts(null);
    setError("");
    load().catch((e) => setError(e.message));
    api<{ id: string; name: string }[]>("/api/resumes/templates")
      .then((t) => {
        if (t?.length) setTemplates(t);
      })
      .catch(() => undefined);
    api<{ docx_export?: boolean }>("/api/billing/usage")
      .then((u) => setDocxAllowed(Boolean(u.docx_export)))
      .catch(() => setDocxAllowed(false));
  }, [params.id]);

  function hasUnsavedChanges() {
    if (!row) return false;
    return template !== row.template || JSON.stringify(content) !== JSON.stringify(row.content);
  }

  async function persist() {
    await api(`/api/resumes/${params.id}`, {
      method: "PUT",
      body: JSON.stringify({ content, title: row?.title, template }),
    });
    await load();
  }

  async function save() {
    setError("");
    try {
      await persist();
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function exportAs(fmt: "pdf" | "docx") {
    if (!row) return;
    setError("");
    try {
      // Export renders from the stored resume, so anything unsaved has to be
      // written first or the download will not match the preview on screen.
      if (hasUnsavedChanges()) await persist();
      await downloadFile(`/api/resumes/${row.id}/export?fmt=${fmt}`, `${row.title}.${fmt}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : `${fmt.toUpperCase()} export failed`);
    }
  }

  async function tailor() {
    setError("");
    try {
      const created = await api<{ id: number }>("/api/resumes/tailor", {
        method: "POST",
        body: JSON.stringify({ resume_id: Number(params.id), job_description: jd, target_role: row?.target_role || "" }),
      });
      window.location.href = `/app/resume/${created.id}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tailor failed");
    }
  }

  async function runAts() {
    setError("");
    try {
      const res = await api<Record<string, unknown>>("/api/resumes/ats", {
        method: "POST",
        body: JSON.stringify({ resume_id: Number(params.id), job_description: jd }),
      });
      setAts(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "ATS failed");
    }
  }

  async function cover() {
    setError("");
    try {
      const res = await api<{ letter: string; flagged_missing?: string[] }>("/api/resumes/cover-letter", {
        method: "POST",
        body: JSON.stringify({ resume_id: Number(params.id), job_description: jd, style }),
      });
      setLetter(res.letter);
      setLetterFlags((res.flagged_missing || []).filter(Boolean));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cover letter failed");
    }
  }

  if (!row) {
    return (
      <div>
        <ErrorText error={error} />
        <p className="text-mist">{error ? "Could not load that resume." : "Loading resume…"}</p>
      </div>
    );
  }

  const unsaved = hasUnsavedChanges();

  const metrics = ats
    ? [
        ["ATS Readiness", ats.ats_readiness],
        ["Keyword Alignment", ats.keyword_alignment],
        ["Skill Coverage", ats.skill_coverage],
        ["Experience Relevance", ats.experience_relevance],
        ["Formatting", ats.formatting],
        ["Role Alignment", ats.role_alignment],
      ]
    : [];

  const missingKeywords = (Array.isArray(ats?.missing_keywords) ? ats.missing_keywords : []).map(String).filter(Boolean);
  const atsNotes = (Array.isArray(ats?.notes) ? ats.notes : []).map(String).filter(Boolean);
  const flags = (content.flagged_missing || []).filter(Boolean);
  const contact = content.contact || {};
  const experience = content.experience || [];
  const changeLog = (row.change_log || []).filter(Boolean);

  return (
    <div>
      <PageTitle
        kicker="Resume studio"
        title={row.title}
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" onClick={() => setEditing((v) => !v)}>
              {editing ? "View resume" : "Edit text"}
            </Button>
            <Button variant="ghost" onClick={() => exportAs("pdf")}>
              PDF
            </Button>
            {docxAllowed ? (
              <Button variant="ghost" onClick={() => exportAs("docx")}>
                DOCX
              </Button>
            ) : (
              <Button variant="ghost" href="/app/settings">
                DOCX · Pro
              </Button>
            )}
            <Button onClick={save}>Save</Button>
            <Button
              variant="ghost"
              onClick={async () => {
                setError("");
                try {
                  const copy = await api<{ id: number }>(`/api/resumes/${row.id}/duplicate`, { method: "POST" });
                  router.push(`/app/resume/${copy.id}`);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Could not duplicate");
                }
              }}
            >
              Duplicate
            </Button>
            <Button
              variant="ghost"
              onClick={async () => {
                if (!confirm(`Delete “${row.title}”? This frees a slot on your plan.`)) return;
                setError("");
                try {
                  await api(`/api/resumes/${row.id}`, { method: "DELETE" });
                  router.push("/app/resume");
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Could not delete");
                }
              }}
            >
              Delete
            </Button>
          </div>
        }
      />
      <ErrorText error={error} />
      {flags.length > 0 && (
        <p className="mb-4 text-xs text-mist">
          Missing from your profile (not invented): {flags.join(" · ")}
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        {editing ? (
          <Card className="space-y-3">
            <h2 className="font-display text-2xl">Edit sections</h2>
            <Field label="Template">
              <select className={inputClass} value={template} onChange={(e) => setTemplate(e.target.value)}>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Name">
              <input
                className={inputClass}
                value={contact.name || ""}
                onChange={(e) => setContent({ ...content, contact: { ...contact, name: e.target.value } })}
              />
            </Field>
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Email">
                <input
                  className={inputClass}
                  value={contact.email || ""}
                  onChange={(e) => setContent({ ...content, contact: { ...contact, email: e.target.value } })}
                />
              </Field>
              <Field label="Phone">
                <input
                  className={inputClass}
                  value={contact.phone || ""}
                  onChange={(e) => setContent({ ...content, contact: { ...contact, phone: e.target.value } })}
                />
              </Field>
            </div>
            <Field label="Location">
              <input
                className={inputClass}
                value={contact.location || ""}
                onChange={(e) => setContent({ ...content, contact: { ...contact, location: e.target.value } })}
              />
            </Field>
            <Field label="Summary">
              <textarea
                className={inputClass}
                rows={5}
                value={content.summary || ""}
                onChange={(e) => setContent({ ...content, summary: e.target.value })}
                placeholder="3–4 lines from facts on your profile. Do not invent jobs."
              />
            </Field>
            {(experience.length ? experience : [{}]).map((item, i) => (
              <div key={i} className="rounded-xl border border-ink/10 p-3">
                <div className="grid gap-2 md:grid-cols-2">
                  <input
                    className={inputClass}
                    placeholder="Title"
                    value={String(item.title || "")}
                    onChange={(e) => {
                      const exp = [...(content.experience || [{}])];
                      exp[i] = { ...item, title: e.target.value };
                      setContent({ ...content, experience: exp });
                    }}
                  />
                  <input
                    className={inputClass}
                    placeholder="Company / studio"
                    value={String(item.company || "")}
                    onChange={(e) => {
                      const exp = [...(content.experience || [{}])];
                      exp[i] = { ...item, company: e.target.value };
                      setContent({ ...content, experience: exp });
                    }}
                  />
                </div>
                <textarea
                  className={`${inputClass} mt-2`}
                  rows={4}
                  placeholder="One achievement per line"
                  value={bullets(item).join("\n")}
                  onChange={(e) => {
                    const lines = e.target.value.split("\n").map((x) => x.trim()).filter(Boolean);
                    const exp = [...(content.experience || [{}])];
                    exp[i] = { ...item, responsibilities: lines, achievements: [] };
                    setContent({ ...content, experience: exp });
                  }}
                />
              </div>
            ))}
            {(content.education || [{}]).map((item, i) => (
              <div key={`edu-${i}`} className="rounded-xl border border-ink/10 p-3">
                <div className="grid gap-2 md:grid-cols-2">
                  <input
                    className={inputClass}
                    placeholder="Degree"
                    value={String(item.degree || "")}
                    onChange={(e) => {
                      const edu = [...(content.education || [{}])];
                      edu[i] = { ...item, degree: e.target.value };
                      setContent({ ...content, education: edu });
                    }}
                  />
                  <input
                    className={inputClass}
                    placeholder="School"
                    value={String(item.institution || "")}
                    onChange={(e) => {
                      const edu = [...(content.education || [{}])];
                      edu[i] = { ...item, institution: e.target.value };
                      setContent({ ...content, education: edu });
                    }}
                  />
                </div>
              </div>
            ))}
            {(content.projects || [{}]).map((item, i) => (
              <div key={`proj-${i}`} className="rounded-xl border border-ink/10 p-3">
                <input
                  className={inputClass}
                  placeholder="Project name"
                  value={String(item.name || "")}
                  onChange={(e) => {
                    const projects = [...(content.projects || [{}])];
                    projects[i] = { ...item, name: e.target.value };
                    setContent({ ...content, projects });
                  }}
                />
                <textarea
                  className={`${inputClass} mt-2`}
                  rows={3}
                  placeholder="What you built"
                  value={String(item.description || "")}
                  onChange={(e) => {
                    const projects = [...(content.projects || [{}])];
                    projects[i] = { ...item, description: e.target.value };
                    setContent({ ...content, projects });
                  }}
                />
              </div>
            ))}
            {Object.entries(content.skills || {}).map(([group, values]) => (
              <Field key={group} label={group.replace(/_/g, " ")}>
                <input
                  className={inputClass}
                  value={Array.isArray(values) ? values.join(", ") : ""}
                  onChange={(e) =>
                    setContent({
                      ...content,
                      skills: {
                        ...(content.skills || {}),
                        [group]: e.target.value.split(",").map((x) => x.trim()).filter(Boolean),
                      },
                    })
                  }
                  placeholder="Comma-separated"
                />
              </Field>
            ))}
            <p className="text-xs text-mist">Change log: {(row.change_log || []).slice(-3).join(" · ")}</p>
          </Card>
        ) : (
          <ResumePaper content={content} template={template} targetRole={row.target_role} />
        )}

        <div className="space-y-4">
          <Card className="space-y-3">
            <h2 className="font-display text-2xl">Tailor to a job</h2>
            <p className="text-sm text-mist">Paste a posting. We do not scrape job boards, and we will not invent experience.</p>
            <textarea className={inputClass} rows={8} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste JD here…" />
            <div className="flex flex-wrap gap-2">
              <Button onClick={tailor} disabled={!jd}>
                Tailor (no inventions)
              </Button>
              <Button variant="ink" onClick={runAts} disabled={!jd.trim()}>
                ATS analysis
              </Button>
            </div>
          </Card>
          {metrics.length > 0 && (
            <Card>
              <h2 className="font-display text-2xl">Keyword & completeness check</h2>
              <div className="mt-4 grid grid-cols-2 gap-3">
                {metrics.map(([k, v]) => (
                  <div key={String(k)}>
                    <div className="text-xs text-mist">{String(k)}</div>
                    <div className="font-display text-2xl">{String(v)}%</div>
                  </div>
                ))}
              </div>
              {missingKeywords.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-wide text-mist">Terms in the posting you have not used</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {missingKeywords.slice(0, 24).map((k) => (
                      <span key={k} className="rounded-full border border-copper/30 bg-copper/5 px-2.5 py-1 text-xs">
                        {k}
                      </span>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-mist">
                    Only add a term if it is genuinely true of your experience.
                  </p>
                </div>
              )}
              {atsNotes.length > 0 && (
                <ul className="mt-3 space-y-1 text-xs text-mist">
                  {atsNotes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-xs text-mist">
                Deterministic keyword matching against the pasted job description. It measures coverage of your own
                wording, not whether a real ATS or recruiter will pass you through.
              </p>
            </Card>
          )}
          {changeLog.length > 0 && (
            <Card>
              <h2 className="font-display text-2xl">What changed</h2>
              <ul className="mt-3 space-y-1 text-sm text-mist">
                {changeLog.slice(-8).reverse().map((entry, i) => (
                  <li key={`${entry}-${i}`}>{entry}</li>
                ))}
              </ul>
            </Card>
          )}
          <Card className="space-y-3">
            <h2 className="font-display text-2xl">Cover letter</h2>
            <Field label="Style">
              <select className={inputClass} value={style} onChange={(e) => setStyle(e.target.value)}>
                {["professional", "concise", "technical", "graduate", "career-switcher"].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </Field>
            <Button variant="ghost" onClick={cover} disabled={!jd}>
              Generate from profile + JD
            </Button>
            {letterFlags.length > 0 && (
              <ul className="space-y-1 rounded-xl border border-copper/30 bg-copper/5 px-3 py-2 text-xs text-mist">
                {letterFlags.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            )}
            {letter && <pre className="whitespace-pre-wrap text-sm leading-relaxed">{letter}</pre>}
          </Card>
        </div>
      </div>
    </div>
  );
}
