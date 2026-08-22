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
    copper: "bg-copper text-paper hover:bg-[#b45e30]",
    ink: "bg-ink text-paper hover:bg-coal",
    ghost: "bg-transparent text-ink border border-ink/15 hover:bg-cream",
    paper: "bg-paper text-ink border border-ink/10 hover:bg-white",
  }[variant];
  const cls = `inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition disabled:opacity-50 ${styles} ${className}`;
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
      <span className="text-xs uppercase tracking-[0.16em] text-mist">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-ink/10 bg-white/70 px-3 py-2.5 text-sm outline-none ring-copper/30 focus:ring-2";

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
        className="absolute right-3 top-1/2 -translate-y-1/2 text-mist hover:text-ink"
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-ink/10 bg-white/70 p-5 shadow-lift ${className}`}>{children}</div>;
}

export function Score({ value, label }: { value: number; label: string }) {
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
        <div className="text-xs text-mist">AI estimate, not a guarantee</div>
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
      className="fixed inset-0 z-[80] grid place-items-center bg-ink/45 p-4"
      role="dialog"
      aria-modal="true"
      onClick={() => setAlert(null)}
    >
      <div className="w-full max-w-md rounded-3xl bg-paper p-6 shadow-lift" onClick={(e) => e.stopPropagation()}>
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
    <div className="mx-auto w-full max-w-md">
      <h1 className="font-display text-4xl">{title}</h1>
      <p className="mt-2 text-mist">{subtitle}</p>
      <form onSubmit={handle} className="mt-8 space-y-4">
        {extra}
        <ErrorText error={error} />
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? "Working…" : submitLabel}
        </Button>
      </form>
    </div>
  );
}

export function useNav() {
  return useRouter();
}
