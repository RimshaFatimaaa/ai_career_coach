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
import { BrandMark } from "@/components/pastel";
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
    <div className="flex min-h-screen">
      <aside className="sticky top-0 z-20 flex h-screen w-64 flex-col border-r border-[#ece3fb] bg-white/75 text-[#3d3453] backdrop-blur-md">
        <div className="px-6 pb-2 pt-7">
          <BrandMark href="/app" />
        </div>
        <p className="px-6 text-[11px] uppercase tracking-[0.22em] text-[#8b83a3]">AI career coach</p>
        <nav className="mt-8 flex-1 space-y-1 overflow-y-auto px-3">
          {links.map((l) => {
            const active = path === l.href || (l.href !== "/app" && path.startsWith(l.href));
            const Icon = l.icon;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                  active
                    ? "bg-[#a78bfa] text-white shadow-[0_14px_26px_rgba(167,139,250,0.35)]"
                    : "text-[#6b6285] hover:bg-[#faf7ff] hover:text-[#3d3453]"
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
                path.startsWith("/app/admin")
                  ? "bg-[#a78bfa] text-white shadow-[0_14px_26px_rgba(167,139,250,0.35)]"
                  : "text-[#6b6285] hover:bg-[#faf7ff]"
              }`}
            >
              <Shield size={16} />
              Admin
            </Link>
          )}
        </nav>
        <div className="border-t border-[#ece3fb] p-4">
          <div className="text-sm">{user.full_name}</div>
          <div className="text-xs capitalize text-[#8b83a3]">{user.plan} plan</div>
          <button
            type="button"
            className="mt-3 flex cursor-pointer items-center gap-2 text-xs text-[#8b83a3] hover:text-[#3d3453]"
            onClick={() => {
              clearSession();
              router.push("/");
            }}
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
      <main className="relative z-10 min-w-0 flex-1 overflow-y-auto p-8">{children}</main>
    </div>
  );
}

export function PageTitle({ title, action }: { kicker?: string; title: string; action?: React.ReactNode }) {
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
        <h1 className="font-display text-4xl tracking-tight">{title}</h1>
        {action}
      </div>
    </div>
  );
}
