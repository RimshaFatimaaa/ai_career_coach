"use client";

import type { ReactNode } from "react";

type Content = {
  contact?: Record<string, string>;
  summary?: string;
  skills?: Record<string, string[]>;
  experience?: Record<string, unknown>[];
  education?: Record<string, unknown>[];
  projects?: Record<string, unknown>[];
};

function blank(value: unknown): boolean {
  if (value == null) return true;
  if (typeof value === "string") {
    return ["", "nothing", "n/a", "na", "-", "none"].includes(value.trim().toLowerCase());
  }
  if (Array.isArray(value)) return value.every(blank);
  if (typeof value === "object") return Object.values(value as object).every(blank);
  return false;
}

function skillGroups(skills?: Record<string, string[]>) {
  return Object.entries(skills || {})
    .filter(([, v]) => Array.isArray(v) && v.length)
    .map(([k, v]) => ({ group: k.replace(/_/g, " "), items: v }));
}

function bullets(item: Record<string, unknown>) {
  const a = Array.isArray(item.responsibilities) ? item.responsibilities : [];
  const b = Array.isArray(item.achievements) ? item.achievements : [];
  return [...a, ...b].map(String).filter((x) => !blank(x));
}

const THEMES: Record<string, { accent: string; header: string; name: string; lined: boolean; compact: boolean; center: boolean }> = {
  ats_classic: { accent: "#1c1c1c", header: "plain", name: "text-[34px]", lined: true, compact: false, center: false },
  modern_ats: { accent: "#b05226", header: "banner", name: "text-[30px]", lined: false, compact: false, center: true },
  technical: { accent: "#124e66", header: "plain", name: "text-[30px]", lined: true, compact: false, center: false },
  graduate: { accent: "#245c48", header: "plain", name: "text-[30px]", lined: true, compact: false, center: false },
  executive: { accent: "#1c2030", header: "banner", name: "text-[32px]", lined: false, compact: false, center: false },
  compact: { accent: "#373737", header: "plain", name: "text-[26px]", lined: true, compact: true, center: false },
  portfolio: { accent: "#843426", header: "plain", name: "text-[32px]", lined: true, compact: false, center: true },
  two_tone: { accent: "#163a58", header: "banner", name: "text-[30px]", lined: false, compact: false, center: false },
};

function Section({
  title,
  accent,
  children,
  compact,
}: {
  title: string;
  accent: string;
  children: ReactNode;
  compact?: boolean;
}) {
  return (
    <section className={compact ? "mt-4" : "mt-6"}>
      <h2 className="border-b pb-1 text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: accent, borderColor: accent }}>
        {title}
      </h2>
      <div className={compact ? "mt-2" : "mt-3"}>{children}</div>
    </section>
  );
}

export function ResumePaper({
  content,
  template = "ats_classic",
  targetRole,
}: {
  content: Content;
  template?: string;
  targetRole?: string;
}) {
  const theme = THEMES[template] || THEMES.ats_classic;
  const contact = content.contact || {};
  const skills = skillGroups(content.skills);
  const experience = content.experience || [];
  const education = content.education || [];
  const projects = content.projects || [];
  const summary = blank(content.summary) ? "" : String(content.summary);
  const headline = contact.headline || targetRole || "";
  const meta = [contact.email, contact.phone, contact.location, contact.links].filter((x) => !blank(x)).join("  ·  ");

  const order =
    template === "technical"
      ? ["skills", "projects", "experience", "education", "summary"]
      : template === "graduate"
        ? ["education", "projects", "skills", "experience", "summary"]
        : template === "executive"
          ? ["summary", "experience", "education", "skills", "projects"]
          : template === "portfolio"
            ? ["summary", "projects", "skills", "experience", "education"]
            : template === "compact"
              ? ["summary", "experience", "skills", "education", "projects"]
              : template === "two_tone"
                ? ["summary", "experience", "projects", "skills", "education"]
                : ["summary", "skills", "experience", "projects", "education"];

  const header = (
    <header className={theme.header === "banner" ? "px-10 py-7 text-white sm:px-12" : "px-10 pb-5 pt-12 sm:px-14"} style={theme.header === "banner" ? { background: theme.accent } : undefined}>
      <h1 className={`font-display tracking-tight ${theme.name} ${theme.center ? "text-center" : ""}`}>{contact.name || "Your name"}</h1>
      {headline && (
        <p className={`mt-1 text-sm ${theme.center ? "text-center" : ""} ${theme.header === "banner" ? "text-white/85" : "text-mist"}`}>{headline}</p>
      )}
      <p className={`mt-2 text-[13px] ${theme.center ? "text-center" : ""} ${theme.header === "banner" ? "text-white/80" : "text-mist"}`}>
        {meta || "Add email and location in Edit text"}
      </p>
    </header>
  );

  const body = (
    <div className={`px-10 pb-12 sm:px-14 ${theme.header === "banner" ? "pt-6" : ""} ${theme.compact ? "text-[13px] leading-snug" : "text-sm leading-relaxed"}`}>
      {order.map((section) => {
        if (section === "summary") {
          return (
            <Section key={section} title={template === "executive" ? "Professional profile" : "Summary"} accent={theme.accent} compact={theme.compact}>
              <p>{summary || "Add a short professional summary from facts on your career profile."}</p>
            </Section>
          );
        }
        if (section === "skills" && skills.length) {
          return (
            <Section key={section} title={template === "technical" ? "Technical skills" : "Skills"} accent={theme.accent} compact={theme.compact}>
              <ul className="space-y-1">
                {skills.map((s) => (
                  <li key={s.group}>
                    <span className="capitalize text-mist">{s.group}: </span>
                    {s.items.join(" · ")}
                  </li>
                ))}
              </ul>
            </Section>
          );
        }
        if (section === "experience") {
          const rows = experience.filter((e) => !blank(e.title) || !blank(e.company));
          return (
            <Section key={section} title={template === "executive" ? "Leadership & experience" : "Experience"} accent={theme.accent} compact={theme.compact}>
              {rows.length === 0 ? (
                <p className="text-mist">No roles on file yet. Add internships, freelance, studio, teaching, or volunteer work.</p>
              ) : (
                <div className="space-y-4">
                  {rows.map((item, i) => (
                    <div key={i}>
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="font-semibold">
                          {String(item.title || "Role")}
                          {item.company ? `  ·  ${String(item.company)}` : ""}
                        </p>
                        <p className="text-xs tracking-wide text-mist">
                          {[item.start_date, item.end_date].filter((x) => !blank(x)).map(String).join(" – ")}
                        </p>
                      </div>
                      <ul className="mt-1 list-disc space-y-0.5 pl-5">
                        {bullets(item).map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          );
        }
        if (section === "education") {
          const rows = education.filter((e) => !blank(e.degree) || !blank(e.institution));
          return (
            <Section key={section} title="Education" accent={theme.accent} compact={theme.compact}>
              {rows.length === 0 ? (
                <p className="text-mist">Add a degree or program on your career profile.</p>
              ) : (
                <div className="space-y-2">
                  {rows.map((item, i) => (
                    <div key={i} className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="font-semibold">
                        {String(item.degree || "Program")}
                        {item.institution ? `  ·  ${String(item.institution)}` : ""}
                      </p>
                      <p className="text-xs text-mist">{String(item.graduation_date || "")}</p>
                      {!blank(item.major) || !blank(item.gpa) ? (
                        <p className="w-full text-mist">
                          {[item.major, item.gpa ? `GPA ${item.gpa}` : ""].filter((x) => !blank(x)).join(" · ")}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </Section>
          );
        }
        if (section === "projects") {
          const rows = projects.filter((p) => !blank(p.name));
          if (!rows.length) return null;
          return (
            <Section key={section} title={template === "portfolio" ? "Selected work" : "Projects"} accent={theme.accent} compact={theme.compact}>
              <div className="space-y-3">
                {rows.map((item, i) => (
                  <div key={i}>
                    <p className="font-semibold">
                      {String(item.name)}
                      {item.role ? `  ·  ${String(item.role)}` : ""}
                    </p>
                    {!blank(item.description) && <p className="text-mist">{String(item.description)}</p>}
                    {Array.isArray(item.technologies) && item.technologies.length > 0 && (
                      <p className="text-xs italic text-mist">{item.technologies.map(String).join(" · ")}</p>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          );
        }
        return null;
      })}
    </div>
  );

  return (
    <article className={`resume-sheet mx-auto w-full max-w-[820px] overflow-hidden ${template === "two_tone" ? "border-l-8" : ""}`} style={template === "two_tone" ? { borderLeftColor: theme.accent } : undefined}>
      {header}
      {body}
    </article>
  );
}
