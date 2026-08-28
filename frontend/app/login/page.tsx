"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Lock, Mail, ArrowLeft } from "lucide-react";
import { FormEvent, useState } from "react";
import { BrandMark, TiltCard } from "@/components/pastel";
import { ErrorText } from "@/components/ui";
import { api, setSession } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handle(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const fd = new FormData(e.currentTarget);
      const data = await api<{ access_token: string; user: unknown }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: fd.get("email"), password: fd.get("password") }),
      });
      setSession(data.access_token, data.user);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center px-5 py-[60px]">
      <Link
        href="/"
        className="absolute left-6 top-6 z-30 inline-flex items-center gap-1.5 text-sm"
        style={{ color: "#8b83a3" }}
      >
        <ArrowLeft size={18} />
        Back
      </Link>
      <TiltCard width={460}>
        <BrandMark />
        <div className="font-display mt-[26px]" style={{ fontSize: 27, color: "#3d3453" }}>
          Welcome back
        </div>
        <div style={{ fontSize: 13, color: "#8b83a3", marginTop: 4 }}>Sign in to your career workspace.</div>
        <form onSubmit={handle} className="mt-[26px] flex flex-col gap-3">
          <label className="field-lilac">
            <Mail size={16} color="#b3a6d1" />
            <input name="email" type="email" required placeholder="you@example.com" />
          </label>
          <label className="field-lilac">
            <Lock size={16} color="#b3a6d1" />
            <input name="password" type={show ? "text" : "password"} required placeholder="••••••••••" autoComplete="current-password" />
            <button type="button" tabIndex={-1} aria-label={show ? "Hide password" : "Show password"} onClick={() => setShow((v) => !v)} className="ml-auto">
              {show ? <EyeOff size={16} color="#b3a6d1" /> : <Eye size={16} color="#b3a6d1" />}
            </button>
          </label>
          <ErrorText error={error} />
          <button type="submit" disabled={busy} className="btn-lilac whitespace-nowrap">
            {busy ? "Working…" : "Sign in"}
          </button>
          <div className="my-0.5 flex items-center gap-2.5">
            <div className="h-px flex-1" style={{ background: "#ece3fb" }} />
            <span style={{ fontSize: 11, color: "#b3a6d1" }}>or</span>
            <div className="h-px flex-1" style={{ background: "#ece3fb" }} />
          </div>
          <p className="text-center" style={{ fontSize: 12, color: "#8b83a3" }}>
            New here?{" "}
            <Link href="/signup" style={{ color: "#a78bfa" }}>
              Create your profile
            </Link>
          </p>
          <p className="text-center" style={{ fontSize: 12, color: "#8b83a3" }}>
            <Link href="/forgot-password" style={{ color: "#a78bfa" }}>
              Forgot password?
            </Link>
          </p>
        </form>
      </TiltCard>
    </div>
  );
}
