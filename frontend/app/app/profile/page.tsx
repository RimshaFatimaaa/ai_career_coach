"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Edu = {
  degree: string;
  institution: string;
  major: string;
  start_date: string;
  graduation_date: string;
  gpa: string;
  coursework: string;
};
type Exp = {
  company: string;
  title: string;
  start_date: string;
  end_date: string;
  responsibilities: string;
  achievements: string;
  technologies: string;
  industry: string;
};
type Proj = {
  name: string;
  description: string;
  technologies: string;
  role: string;
  results: string;
  github: string;
  demo: string;
};

const emptySkills = {
  craft: "",
  domain: "",
  programming: "",
  frameworks: "",
  tools: "",
  platforms: "",
  technical: "",
  soft: "",
  certifications: "",
};

const skillLabels: Record<string, string> = {
  craft: "Craft / medium (drawing, CAD, studio, clinical…)",
  domain: "Domain knowledge",
  programming: "Programming (only if relevant)",
  frameworks: "Frameworks / methods",
  tools: "Tools & software",
  platforms: "Platforms",
  technical: "Technical / specialist",
  soft: "Soft skills",
  certifications: "Certifications",
};

const blankEdu = (): Edu => ({
  degree: "",
  institution: "",
  major: "",
  start_date: "",
  graduation_date: "",
  gpa: "",
  coursework: "",
});
const blankExp = (): Exp => ({
  company: "",
  title: "",
  start_date: "",
  end_date: "",
  responsibilities: "",
  achievements: "",
  technologies: "",
  industry: "",
});
const blankProj = (): Proj => ({
  name: "",
  description: "",
  technologies: "",
  role: "",
  results: "",
  github: "",
  demo: "",
});

function csv(list?: unknown) {
  return Array.isArray(list) ? list.join(", ") : "";
}
function split(s: string) {
  return s.split(",").map((x) => x.trim()).filter(Boolean);
}
function lines(s: string) {
  return s.split("\n").map((x) => x.trim()).filter(Boolean);
}

export default function ProfilePage() {
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [form, setForm] = useState<Record<string, string>>({});
  const [skills, setSkills] = useState(emptySkills);
  const savedRef = useRef<HTMLDivElement>(null);
  const [education, setEducation] = useState<Edu[]>([blankEdu()]);
  const [experience, setExperience] = useState<Exp[]>([blankExp()]);
  const [projects, setProjects] = useState<Proj[]>([blankProj()]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api<{
      full_name: string;
      country: string;
      city: string;
      professional_status: string;
      headline: string;
      summary: string;
      education: Record<string, unknown>[];
      experience: Record<string, unknown>[];
      skills: Record<string, string[]>;
      projects: Record<string, unknown>[];
      career_goals: Record<string, string>;
      linkedin_url?: string;
      github_username?: string;
    }>("/api/profile").then((p) => {
      setForm({
        full_name: p.full_name || "",
        country: p.country,
        city: p.city,
        professional_status: p.professional_status,
        headline: p.headline,
        summary: p.summary,
        linkedin_url: p.linkedin_url || "",
        github_username: p.github_username || "",
        desired_role: p.career_goals?.desired_role || "",
        desired_career: p.career_goals?.desired_career || "",
        desired_industry: p.career_goals?.desired_industry || "",
        experience_level: p.career_goals?.experience_level || "entry",
        short_term_goal: p.career_goals?.short_term_goal || "",
        long_term_goal: p.career_goals?.long_term_goal || "",
      });
      setSkills({
        ...emptySkills,
        craft: csv(p.skills?.craft),
        domain: csv(p.skills?.domain),
        programming: csv(p.skills?.programming),
        frameworks: csv(p.skills?.frameworks),
        tools: csv(p.skills?.tools),
        platforms: csv(p.skills?.platforms),
        technical: csv(p.skills?.technical),
        soft: csv(p.skills?.soft),
        certifications: csv(p.skills?.certifications),
      });
      setEducation(
        (p.education || []).length
          ? p.education.map((e) => ({
              degree: String(e.degree || ""),
              institution: String(e.institution || ""),
              major: String(e.major || ""),
              start_date: String(e.start_date || ""),
              graduation_date: String(e.graduation_date || ""),
              gpa: String(e.gpa || ""),
              coursework: csv(e.coursework),
            }))
          : [blankEdu()]
      );
      setExperience(
        (p.experience || []).length
          ? p.experience.map((e) => ({
              company: String(e.company || ""),
              title: String(e.title || ""),
              start_date: String(e.start_date || ""),
              end_date: String(e.end_date || ""),
              responsibilities: Array.isArray(e.responsibilities) ? e.responsibilities.join("\n") : "",
              achievements: Array.isArray(e.achievements) ? e.achievements.join("\n") : "",
              technologies: csv(e.technologies),
              industry: String(e.industry || ""),
            }))
          : [blankExp()]
      );
      setProjects(
        (p.projects || []).length
          ? p.projects.map((e) => ({
              name: String(e.name || ""),
              description: String(e.description || ""),
              technologies: csv(e.technologies),
              role: String(e.role || ""),
              results: String(e.results || ""),
              github: String(e.github || ""),
              demo: String(e.demo || ""),
            }))
          : [blankProj()]
      );
      setLoaded(true);
    }).catch((e) => {
      setError(e instanceof Error ? e.message : "Could not load your profile. Refresh before saving.");
      setLoaded(false);
    });
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!loaded) {
      setError("Wait for your profile to load before saving, or refresh the page.");
      return;
    }
    setError("");
    setSaved("");
    try {
      const payload = {
        full_name: form.full_name,
        country: form.country,
        city: form.city,
        professional_status: form.professional_status,
        headline: form.headline,
        summary: form.summary,
        linkedin_url: form.linkedin_url,
        github_username: form.github_username,
        skills: Object.fromEntries(Object.entries(skills).map(([k, v]) => [k, split(v)])),
        career_goals: {
          desired_role: form.desired_role,
          desired_career: form.desired_career,
          desired_industry: form.desired_industry,
          experience_level: form.experience_level,
          short_term_goal: form.short_term_goal,
          long_term_goal: form.long_term_goal,
        },
        education: education
          .filter((x) => x.degree || x.institution)
          .map((x) => ({ ...x, coursework: split(x.coursework) })),
        experience: experience
          .filter((x) => x.company || x.title)
          .map((x) => ({
            ...x,
            responsibilities: lines(x.responsibilities),
            achievements: lines(x.achievements),
            technologies: split(x.technologies),
          })),
        projects: projects
          .filter((x) => x.name)
          .map((x) => ({ ...x, technologies: split(x.technologies) })),
      };
      await api("/api/profile", { method: "PUT", body: JSON.stringify(payload) });
      setSaved("Saved. Your career profile is stored. Coaching, resumes, and interviews now use these facts.");
      requestAnimationFrame(() => savedRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    }
  }

  function loadStudentExample() {
    setEducation([
      {
        degree: "BS Artificial Intelligence",
        institution: "UMT Lahore",
        major: "Artificial Intelligence",
        start_date: "2022-09",
        graduation_date: "2026-06",
        gpa: "3.7",
        coursework: "Machine Learning, NLP, Data Structures, Databases",
      },
    ]);
    setExperience([
      {
        company: "Campus AI Club",
        title: "Project Lead",
        start_date: "2024-01",
        end_date: "Present",
        responsibilities: "Led a retrieval chatbot for course notes\nRan weekly build sessions for 12 members",
        achievements: "Shipped a demo used by 40 students\nCut answer lookup time for club notes",
        technologies: "Python, LangChain, FastAPI, SQL",
        industry: "Education",
      },
    ]);
    setProjects([
      {
        name: "AI Career Coach",
        description: "Profile-grounded coaching, resume, and interview platform",
        technologies: "Next.js, FastAPI, LangGraph, Supabase",
        role: "Builder",
        results: "Working MVP with three product pillars",
        github: "https://github.com/example/ai-career-coach",
        demo: "http://localhost:3000",
      },
    ]);
    setSkills({
      ...emptySkills,
      craft: "Technical writing, prompt design",
      domain: "Applied AI, education technology",
      programming: "Python, SQL",
      frameworks: "LangChain, LangGraph, FastAPI, Next.js, LLM APIs",
      tools: "Git, Docker",
      platforms: "Supabase, Cloudflare R2",
      technical: "RAG, prompt engineering, REST APIs",
      soft: "Communication, teaching, collaboration",
      certifications: "None yet — building a public project portfolio",
    });
    setForm({
      city: "Lahore",
      country: "Pakistan",
      headline: "BS AI student targeting AI Engineer roles",
      summary:
        "BS AI student at UMT with Python, SQL, LangChain, and project experience. Targeting AI Engineer roles and shipping small production demos.",
      desired_role: "AI Engineer",
      desired_career: "Applied AI",
      desired_industry: "SaaS",
      professional_status: "student",
      experience_level: "entry",
      short_term_goal: "Ship two portfolio AI apps and intern as an AI engineer",
      long_term_goal: "Become an applied AI engineer who owns LLM features in production",
      linkedin_url: "https://www.linkedin.com/in/example-rimsha",
      github_username: "rimsha",
    });
    setSaved("Student example is ready. Save your profile to keep it.");
    setError("");
    setLoaded(true);
  }

  const set = (k: string) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  return (
    <form onSubmit={save}>
      <PageTitle
        kicker="Core data model"
        title="Career profile"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" type="button" onClick={loadStudentExample}>
              Load student example
            </Button>
            <Button type="submit" disabled={!loaded}>Save profile</Button>
          </div>
        }
      />
      <ErrorText error={error} />
      <div ref={savedRef}>
        {saved && (
          <p className="mb-4 rounded-xl border border-moss/20 bg-sage/20 px-4 py-3 text-sm font-medium text-moss">
            {saved}
          </p>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-4">
          <h2 className="font-display text-2xl">Personal</h2>
          <Field label="Full name">
            <input
              className={inputClass}
              value={form.full_name || ""}
              onChange={set("full_name")}
              placeholder="The name that appears on your resume"
            />
          </Field>
          <Field label="Headline">
            <input className={inputClass} value={form.headline || ""} onChange={set("headline")} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="City">
              <input className={inputClass} value={form.city || ""} onChange={set("city")} />
            </Field>
            <Field label="Country">
              <input className={inputClass} value={form.country || ""} onChange={set("country")} />
            </Field>
          </div>
          <Field label="Professional status">
            <select className={inputClass} value={form.professional_status || "student"} onChange={set("professional_status")}>
              <option value="student">Student</option>
              <option value="fresh_graduate">Fresh graduate</option>
              <option value="career_switcher">Career switcher</option>
              <option value="professional">Working professional</option>
            </select>
          </Field>
          <Field label="Summary">
            <textarea className={inputClass} rows={4} value={form.summary || ""} onChange={set("summary")} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="LinkedIn URL">
              <input className={inputClass} value={form.linkedin_url || ""} onChange={set("linkedin_url")} placeholder="https://www.linkedin.com/in/…" />
            </Field>
            <Field label="GitHub username">
              <input className={inputClass} value={form.github_username || ""} onChange={set("github_username")} placeholder="your-handle" />
            </Field>
          </div>
        </Card>
        <Card className="space-y-4">
          <h2 className="font-display text-2xl">Career goals</h2>
          <Field label="Desired role">
          <input className={inputClass} value={form.desired_role || ""} onChange={set("desired_role")} placeholder="Architect, Teacher, Nurse, AI Engineer…" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Career">
              <input className={inputClass} value={form.desired_career || ""} onChange={set("desired_career")} />
            </Field>
            <Field label="Industry">
              <input className={inputClass} value={form.desired_industry || ""} onChange={set("desired_industry")} />
            </Field>
          </div>
          <Field label="Experience level">
            <select className={inputClass} value={form.experience_level || "entry"} onChange={set("experience_level")}>
              <option value="intern">Intern</option>
              <option value="entry">Entry</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
            </select>
          </Field>
          <Field label="Short-term goal">
            <input className={inputClass} value={form.short_term_goal || ""} onChange={set("short_term_goal")} />
          </Field>
          <Field label="Long-term goal">
            <input className={inputClass} value={form.long_term_goal || ""} onChange={set("long_term_goal")} />
          </Field>
        </Card>
        <Card className="space-y-3 md:col-span-2">
          <h2 className="font-display text-2xl">Skills</h2>
          <p className="text-sm text-mist">Comma-separated. Use whatever is real for your field — studio skills, CAD, languages, clinical tools, not just programming.</p>
          <div className="grid gap-3 md:grid-cols-2">
            {Object.keys(emptySkills).map((k) => (
              <Field key={k} label={skillLabels[k] || k}>
                <input
                  className={inputClass}
                  value={skills[k as keyof typeof skills] ?? ""}
                  onChange={(e) => setSkills({ ...skills, [k]: e.target.value })}
                />
              </Field>
            ))}
          </div>
        </Card>
      </div>

      <section className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-2xl">Education</h2>
          <Button type="button" variant="ghost" onClick={() => setEducation([...education, blankEdu()])}>
            Add school
          </Button>
        </div>
        {education.map((row, i) => (
          <Card key={i} className="grid gap-3 md:grid-cols-2">
            <Field label="Degree">
              <input className={inputClass} value={row.degree} onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, degree: e.target.value } : x)))} />
            </Field>
            <Field label="Institution">
              <input className={inputClass} value={row.institution} onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, institution: e.target.value } : x)))} />
            </Field>
            <Field label="Major">
              <input className={inputClass} value={row.major} onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, major: e.target.value } : x)))} />
            </Field>
            <Field label="GPA / CGPA">
              <input className={inputClass} value={row.gpa} onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, gpa: e.target.value } : x)))} />
            </Field>
            <Field label="Start">
              <input className={inputClass} value={row.start_date} placeholder="2022-09" onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, start_date: e.target.value } : x)))} />
            </Field>
            <Field label="Graduation">
              <input className={inputClass} value={row.graduation_date} onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, graduation_date: e.target.value } : x)))} />
            </Field>
            <div className="md:col-span-2">
              <Field label="Coursework (comma-separated)">
                <input className={inputClass} value={row.coursework} onChange={(e) => setEducation(education.map((x, n) => (n === i ? { ...x, coursework: e.target.value } : x)))} />
              </Field>
            </div>
            <button type="button" className="text-left text-xs text-copper" onClick={() => setEducation(education.filter((_, n) => n !== i))}>
              Remove
            </button>
          </Card>
        ))}
      </section>

      <section className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-2xl">Experience</h2>
          <Button type="button" variant="ghost" onClick={() => setExperience([...experience, blankExp()])}>
            Add role
          </Button>
        </div>
        {experience.map((row, i) => (
          <Card key={i} className="grid gap-3 md:grid-cols-2">
            <Field label="Company">
              <input className={inputClass} value={row.company} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, company: e.target.value } : x)))} />
            </Field>
            <Field label="Title">
              <input className={inputClass} value={row.title} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, title: e.target.value } : x)))} />
            </Field>
            <Field label="Start">
              <input className={inputClass} value={row.start_date} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, start_date: e.target.value } : x)))} />
            </Field>
            <Field label="End">
              <input className={inputClass} value={row.end_date} placeholder="Present" onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, end_date: e.target.value } : x)))} />
            </Field>
            <div className="md:col-span-2">
              <Field label="Responsibilities (one per line)">
                <textarea className={inputClass} rows={3} value={row.responsibilities} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, responsibilities: e.target.value } : x)))} />
              </Field>
            </div>
            <div className="md:col-span-2">
              <Field label="Achievements (one per line — only real metrics)">
                <textarea className={inputClass} rows={3} value={row.achievements} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, achievements: e.target.value } : x)))} />
              </Field>
            </div>
            <Field label="Tools / software">
              <input className={inputClass} value={row.technologies} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, technologies: e.target.value } : x)))} />
            </Field>
            <Field label="Industry">
              <input className={inputClass} value={row.industry} onChange={(e) => setExperience(experience.map((x, n) => (n === i ? { ...x, industry: e.target.value } : x)))} />
            </Field>
            <button type="button" className="text-left text-xs text-copper" onClick={() => setExperience(experience.filter((_, n) => n !== i))}>
              Remove
            </button>
          </Card>
        ))}
      </section>

      <section className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-2xl">Projects</h2>
          <Button type="button" variant="ghost" onClick={() => setProjects([...projects, blankProj()])}>
            Add project
          </Button>
        </div>
        {projects.map((row, i) => (
          <Card key={i} className="grid gap-3 md:grid-cols-2">
            <Field label="Name">
              <input className={inputClass} value={row.name} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, name: e.target.value } : x)))} />
            </Field>
            <Field label="Your role">
              <input className={inputClass} value={row.role} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, role: e.target.value } : x)))} />
            </Field>
            <div className="md:col-span-2">
              <Field label="Description">
                <textarea className={inputClass} rows={3} value={row.description} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, description: e.target.value } : x)))} />
              </Field>
            </div>
            <Field label="Tools / media">
              <input className={inputClass} value={row.technologies} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, technologies: e.target.value } : x)))} />
            </Field>
            <Field label="Results">
              <input className={inputClass} value={row.results} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, results: e.target.value } : x)))} />
            </Field>
            <Field label="GitHub">
              <input className={inputClass} value={row.github} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, github: e.target.value } : x)))} />
            </Field>
            <Field label="Demo">
              <input className={inputClass} value={row.demo} onChange={(e) => setProjects(projects.map((x, n) => (n === i ? { ...x, demo: e.target.value } : x)))} />
            </Field>
            <button type="button" className="text-left text-xs text-copper" onClick={() => setProjects(projects.filter((_, n) => n !== i))}>
              Remove
            </button>
          </Card>
        ))}
      </section>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={!loaded}>Save profile</Button>
        {saved && <span className="text-sm font-medium text-moss">{saved}</span>}
      </div>
    </form>
  );
}
