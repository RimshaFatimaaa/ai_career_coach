import Link from "next/link";
import { Button } from "@/components/ui";

export default function HomePage() {
  return (
    <div className="paper-grid min-h-screen bg-paper text-ink">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link href="/" className="font-display text-2xl">
          Atelier
        </Link>
        <div className="flex items-center gap-3">
          <Button href="/login" variant="ghost">
            Sign in
          </Button>
          <Button href="/signup">Start free</Button>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-10">
        <p className="text-xs uppercase tracking-[0.28em] text-copper">Career coaching · Resume studio · Interview coach</p>
        <h1 className="mt-4 max-w-4xl font-display text-6xl leading-[1.05] tracking-tight md:text-7xl">
          One AI that knows your career — not a chatbot that forgets it.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-mist">
          Build a profile once. Coaching, skill-gap analysis, ATS-safe resumes, and adaptive mock interviews
          all read from — and write back to — the same professional memory.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button href="/signup">Create your profile</Button>
          <Button href="#pillars" variant="ghost">
            See the three pillars
          </Button>
        </div>
        <p className="mt-4 text-xs text-mist">Readiness and ATS scores are estimates for personal tracking, never hiring guarantees.</p>
      </section>

      <section id="pillars" className="mx-auto grid max-w-6xl gap-4 px-6 pb-24 md:grid-cols-3">
        {[
          {
            n: "01",
            t: "Career Coach",
            d: "Path comparison, suitability, skill gaps graded Strong to Missing, and a 1–12 month roadmap you can tick off.",
          },
          {
            n: "02",
            t: "Resume Studio",
            d: "Parse an upload, generate from your profile, tailor to a pasted job description, score ATS alignment — without inventing facts.",
          },
          {
            n: "03",
            t: "Interview Coach",
            d: "Behavioral, technical, and Premium voice mocks that follow up when an answer is weak, then a STAR-aware report you can track over time.",
          },
        ].map((p) => (
          <article key={p.n} className="rounded-3xl border border-ink/10 bg-white/60 p-8">
            <div className="font-display text-copper">{p.n}</div>
            <h2 className="mt-3 font-display text-3xl">{p.t}</h2>
            <p className="mt-3 text-sm leading-relaxed text-mist">{p.d}</p>
          </article>
        ))}
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-24">
        <h2 className="font-display text-4xl">State it once.</h2>
        <p className="mt-3 max-w-xl text-mist">
          “I’m a BS AI student. I know Python and LangChain. I want to become an AI Engineer.” Every feature
          after that starts from those facts — and refuses to fabricate the rest.
        </p>
        <ol className="mt-10 grid gap-3 md:grid-cols-4">
          {["Sign up", "Build profile", "Coach + resume", "Mock interview"].map((s, i) => (
            <li key={s} className="rounded-2xl bg-moss px-5 py-6 text-paper">
              <div className="text-xs text-paper/50">Step {i + 1}</div>
              <div className="mt-2 font-display text-2xl">{s}</div>
            </li>
          ))}
        </ol>
      </section>

      <footer className="border-t border-ink/10 px-6 py-10 text-center text-xs text-mist">
        Atelier · AI Career Coach · Not a job board ·{" "}
        <Link href="/privacy" className="text-copper">
          Privacy
        </Link>
        {" · "}
        <Link href="/terms" className="text-copper">
          Terms
        </Link>
      </footer>
    </div>
  );
}
