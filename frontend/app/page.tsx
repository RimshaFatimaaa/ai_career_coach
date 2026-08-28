import Link from "next/link";
import { BrandMark, TiltCard } from "@/components/pastel";

const pillars = [
  {
    n: "01",
    t: "Career Coach",
    d: "Path comparison, skill gaps, and a roadmap you can tick off — all from your saved profile.",
  },
  {
    n: "02",
    t: "Resume Studio",
    d: "Generate, tailor, and score ATS alignment without inventing facts you never had.",
  },
  {
    n: "03",
    t: "Interview Coach",
    d: "Adaptive mocks that follow up when an answer is weak, then a report you can track over time.",
  },
];

export default function HomePage() {
  return (
    <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col px-5 pb-16 pt-24 md:px-8">
      <header className="absolute left-0 right-0 top-0 z-30 mx-auto flex max-w-6xl items-center justify-between px-5 py-6 md:px-8">
        <BrandMark />
        <Link href="/signup" className="btn-lilac !mt-0 !w-auto whitespace-nowrap">
          Start free
        </Link>
      </header>

      <section className="mt-6 grid flex-1 items-center gap-12 lg:grid-cols-[1fr_460px]">
        <div>
          <p className="text-xs uppercase tracking-[0.28em]" style={{ color: "#a78bfa" }}>
            Career coaching · Resume studio · Interview coach
          </p>
          <h1 className="font-display mt-4 max-w-xl text-4xl leading-[1.1] tracking-tight md:text-5xl" style={{ color: "#3d3453" }}>
            One workspace, one Atelier. Every career move ahead.
          </h1>
          <p className="mt-5 max-w-lg text-[15px] leading-relaxed" style={{ color: "#8b83a3" }}>
            Build your profile once. Coaching, skill-gap analysis, ATS-safe resumes, and mock interviews
            all pull from, and write back to, the same professional memory. No repeating yourself.
          </p>
        </div>

        <TiltCard width={460}>
          <BrandMark />
          <div className="font-display mt-[26px]" style={{ fontSize: 27, color: "#3d3453" }}>
            Welcome back
          </div>
          <div style={{ fontSize: 13, color: "#8b83a3", marginTop: 4 }}>
            Sign in to your career workspace.
          </div>
          <div className="mt-[26px] flex flex-col gap-3">
            <Link href="/login" className="btn-lilac whitespace-nowrap">
              Sign in
            </Link>
            <div className="my-0.5 flex items-center gap-2.5">
              <div className="h-px flex-1" style={{ background: "#ece3fb" }} />
              <span style={{ fontSize: 11, color: "#b3a6d1" }}>or</span>
              <div className="h-px flex-1" style={{ background: "#ece3fb" }} />
            </div>
            <Link href="/signup" className="btn-ghost">
              Create your profile
            </Link>
          </div>
        </TiltCard>
      </section>

      <section className="mt-14 grid gap-4 md:grid-cols-3">
        {pillars.map((p) => (
          <article
            key={p.n}
            className="rounded-[22px] p-6"
            style={{
              background: "rgba(255,255,255,0.78)",
              border: "1px solid rgba(255,255,255,0.9)",
              boxShadow: "0 18px 40px rgba(150,110,210,0.16)",
            }}
          >
            <div className="font-display" style={{ color: "#a78bfa" }}>
              {p.n}
            </div>
            <h2 className="font-display mt-2 text-2xl" style={{ color: "#3d3453" }}>
              {p.t}
            </h2>
            <p className="mt-2 text-sm leading-relaxed" style={{ color: "#8b83a3" }}>
              {p.d}
            </p>
          </article>
        ))}
      </section>
    </div>
  );
}
