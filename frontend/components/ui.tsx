"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { FormEvent, InputHTMLAttributes, ReactNode, useEffect, useState } from "react";
import { AppAlert, isPlanLimitMessage, showAppAlert } from "@/lib/api";

export function Button({
  children,
  href,
  onClick,
  variant = "copper",
  type = "button",
  disabled,
  className = "",
}: {
  children: ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: "copper" | "ink" | "ghost" | "paper";
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
}) {
  const styles = {
    copper: "bg-[#a78bfa] text-white shadow-[0_14px_26px_rgba(167,139,250,0.45)] hover:bg-[#9a7df3]",
    ink: "bg-[#4a3f66] text-white hover:bg-[#3d3453]",
    ghost: "bg-[#faf7ff] text-[#3d3453] border border-[#ece3fb] hover:bg-white",
    paper: "bg-white/80 text-[#3d3453] border border-[#ece3fb] hover:bg-white",
  }[variant];
  const cls = `relative z-10 inline-flex cursor-pointer items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`;
  if (href) return <Link href={href} className={cls}>{children}</Link>;
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={cls}>
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-[13px] text-mist">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-[#ece3fb] bg-[#faf7ff] px-3.5 py-3 text-sm text-[#3d3453] outline-none placeholder:text-[#a89bc4] ring-[#a78bfa]/25 focus:ring-2";

export function IconField({
  icon,
  children,
}: {
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute left-3.5 top-1/2 z-[1] -translate-y-1/2 text-[#b3a6d1]">{icon}</span>
      <div className="[&_input]:pl-10">{children}</div>
    </div>
  );
}

export function PasswordInput({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        {...props}
        type={show ? "text" : "password"}
        className={`${inputClass} pr-11 ${className}`}
      />
      <button
        type="button"
        tabIndex={-1}
        aria-label={show ? "Hide password" : "Show password"}
        onClick={() => setShow((v) => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-[#b3a6d1] hover:text-ink"
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-[22px] border border-white/80 bg-white/80 p-5 shadow-lift backdrop-blur-sm ${className}`}>
      {children}
    </div>
  );
}

export function Score({ value, label, hint }: { value: number; label: string; hint?: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="score-ring grid h-14 w-14 place-items-center rounded-full"
        style={{ ["--p" as string]: Math.max(0, Math.min(100, value)) }}
      >
        <div className="grid h-10 w-10 place-items-center rounded-full bg-white text-sm font-medium">{Math.round(value)}</div>
      </div>
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-mist">{hint || `${Math.round(value)} / 100`}</div>
      </div>
    </div>
  );
}

export function ErrorText({ error }: { error?: string }) {
  useEffect(() => {
    if (error) showAppAlert(error);
  }, [error]);
  return null;
}

export function AppAlertModal() {
  const [alert, setAlert] = useState<AppAlert | null>(null);
  useEffect(() => {
    const onAlert = (event: Event) => {
      const detail = (event as CustomEvent<AppAlert>).detail;
      if (detail?.message) setAlert(detail);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAlert(null);
    };
    window.addEventListener("cc-app-alert", onAlert);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("cc-app-alert", onAlert);
      window.removeEventListener("keydown", onKey);
    };
  }, []);
  if (!alert) return null;
  const isLimit = alert.kind === "limit" || isPlanLimitMessage(alert.message);
  return (
    <div
      className="fixed inset-0 z-[80] grid place-items-center bg-[#3d3453]/35 p-4"
      role="dialog"
      aria-modal="true"
      onClick={() => setAlert(null)}
    >
      <div className="w-full max-w-md rounded-[22px] border border-white/90 bg-white/95 p-6 shadow-card" onClick={(e) => e.stopPropagation()}>
        <p className="text-xs uppercase tracking-[0.2em] text-copper">{isLimit ? "Plan limit" : "Notice"}</p>
        <h2 className="mt-2 font-display text-3xl">{isLimit ? "Upgrade to continue" : "Something needs attention"}</h2>
        <p className="mt-3 text-sm leading-relaxed text-ink">{alert.message}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          {isLimit && <Button href="/app/settings">View plans</Button>}
          <Button variant={isLimit ? "ghost" : "copper"} onClick={() => setAlert(null)}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

export const PlanLimitModal = AppAlertModal;

export function AuthForm({
  title,
  subtitle,
  submitLabel,
  onSubmit,
  extra,
}: {
  title: string;
  subtitle: string;
  submitLabel: string;
  onSubmit: (fd: FormData) => Promise<void>;
  extra?: ReactNode;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function handle(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSubmit(new FormData(e.currentTarget));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="w-full">
      <h1 className="font-display" style={{ fontSize: 27, color: "#3d3453" }}>{title}</h1>
      <p className="mt-1" style={{ fontSize: 13, color: "#8b83a3" }}>{subtitle}</p>
      <form onSubmit={handle} className="mt-7 space-y-3">
        {extra}
        <ErrorText error={error} />
        <button type="submit" disabled={busy} className="btn-lilac">
          {busy ? "Working…" : submitLabel}
        </button>
      </form>
    </div>
  );
}

export function useNav() {
  return useRouter();
}
