"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  FileText,
  GitBranch,
  LayoutDashboard,
  LineChart,
  LogOut,
  MessageSquare,
  Mic,
  Settings,
  Shield,
  UserRound,
} from "lucide-react";
import { api, clearSession } from "@/lib/api";

const links = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/profile", label: "Career profile", icon: UserRound },
  { href: "/app/coach", label: "Career coach", icon: MessageSquare },
  { href: "/app/resume", label: "Resume studio", icon: FileText },
  { href: "/app/interview", label: "Interview coach", icon: Mic },
  { href: "/app/insights", label: "Insights", icon: LineChart },
  { href: "/app/imports", label: "LinkedIn / GitHub", icon: GitBranch },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ full_name: string; plan: string; role: string } | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("cc_user");
    if (!raw) {
      router.replace("/login");
      return;
    }
    setUser(JSON.parse(raw));
    api<{ full_name: string; plan: string; role: string }>("/api/auth/me")
      .then((me) => {
        setUser(me);
        const stored = JSON.parse(localStorage.getItem("cc_user") || "{}");
        localStorage.setItem("cc_user", JSON.stringify({ ...stored, ...me }));
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  if (!user) return <div className="grid min-h-screen place-items-center text-mist">Loading atelier…</div>;

  return (
    <div className="flex min-h-screen bg-paper paper-grid">
      <aside className="sticky top-0 flex h-screen w-64 flex-col border-r border-ink/10 bg-[#1C1917] text-paper">
        <Link href="/app" className="px-6 pb-2 pt-7 font-display text-2xl tracking-tight">
          Atelier
        </Link>
        <p className="px-6 text-[11px] uppercase tracking-[0.22em] text-paper/40">AI career coach</p>
        <nav className="mt-8 flex-1 space-y-1 px-3">
          {links.map((l) => {
            const active = path === l.href || (l.href !== "/app" && path.startsWith(l.href));
            const Icon = l.icon;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                  active ? "bg-paper/10 text-paper" : "text-paper/60 hover:bg-paper/5 hover:text-paper"
                }`}
              >
                <Icon size={16} />
                {l.label}
              </Link>
            );
          })}
          {user.role === "admin" && (
            <Link
              href="/app/admin"
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${
                path.startsWith("/app/admin") ? "bg-paper/10" : "text-paper/60 hover:bg-paper/5"
              }`}
            >
              <Shield size={16} />
              Admin
            </Link>
          )}
        </nav>
        <div className="border-t border-paper/10 p-4">
          <div className="text-sm">{user.full_name}</div>
          <div className="text-xs capitalize text-paper/50">{user.plan} plan</div>
          <button
            className="mt-3 flex items-center gap-2 text-xs text-paper/60 hover:text-paper"
            onClick={() => {
              clearSession();
              router.push("/");
            }}
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-8">{children}</main>
    </div>
  );
}

export function PageTitle({ kicker, title, action }: { kicker: string; title: string; action?: React.ReactNode }) {
  const router = useRouter();
  return (
    <div className="mb-8">
      <button
        type="button"
        onClick={() => router.back()}
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-mist transition hover:text-ink"
      >
        <ArrowLeft size={16} />
        Back
      </button>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-mist">{kicker}</div>
          <h1 className="mt-1 font-display text-4xl tracking-tight">{title}</h1>
        </div>
        {action}
      </div>
    </div>
  );
}
