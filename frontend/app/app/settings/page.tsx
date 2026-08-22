"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, PasswordInput, inputClass } from "@/components/ui";
import { api, clearSession } from "@/lib/api";

type Usage = {
  plan: string;
  docx_export: boolean;
  career_memory: boolean;
  voice_interviews?: boolean;
  stripe_enabled?: boolean;
  providers?: string[];
  card_last4?: string;
  card_brand?: string;
  resume_generations: { used: number; limit: number };
  resume_analyses: { used: number; limit: number };
  tailorings: { used: number; limit: number };
  mock_interviews: { used: number; limit: number };
  interview_questions: { used: number; limit: number };
  cover_letters: { used: number; limit: number };
};

const PLANS = [
  { id: "free", price: "$0", note: "1 resume · 2 generations · 1 mock · 1 cover letter / month" },
  { id: "pro", price: "$12.99", note: "Cover letters, DOCX, career memory, higher limits" },
  { id: "premium", price: "$29.99", note: "Highest limits · voice interviews · advanced analytics" },
];

function formatCardNumber(raw: string) {
  return raw
    .replace(/\D/g, "")
    .slice(0, 19)
    .replace(/(\d{4})(?=\d)/g, "$1 ")
    .trim();
}

function formatExpiry(raw: string) {
  const d = raw.replace(/\D/g, "").slice(0, 4);
  if (d.length <= 2) return d;
  return `${d.slice(0, 2)}/${d.slice(2)}`;
}

export default function SettingsPage() {
  const router = useRouter();
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [target, setTarget] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [cardName, setCardName] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [exp, setExp] = useState("");
  const [cvc, setCvc] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const u = await api<Usage>("/api/billing/usage");
    setUsage(u);
    const me = await api<{ plan: string }>("/api/auth/me");
    const raw = localStorage.getItem("cc_user");
    if (raw) {
      const stored = JSON.parse(raw);
      stored.plan = me.plan;
      localStorage.setItem("cc_user", JSON.stringify(stored));
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    const q = new URLSearchParams(window.location.search).get("checkout");
    if (q === "success") setNote("Payment received. Your plan updates once Stripe confirms.");
    if (q === "cancel") setNote("Checkout was cancelled. Your plan was not changed.");
  }, []);

  function resetForm() {
    setTarget(null);
    setPassword("");
    setCardName("");
    setCardNumber("");
    setExp("");
    setCvc("");
  }

  async function startCheckout(e: FormEvent) {
    e.preventDefault();
    if (!target) return;
    setBusy(true);
    setError("");
    try {
      const body =
        target === "free"
          ? { plan: target, password }
          : {
              plan: target,
              card_name: cardName,
              card_number: cardNumber.replace(/\s/g, ""),
              exp,
              cvc,
            };
      const res = await api<{
        status: string;
        checkout_url?: string;
        plan?: string;
        note?: string;
        card_last4?: string;
      }>("/api/billing/checkout", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (res.status === "stripe" && res.checkout_url) {
        window.location.href = res.checkout_url;
        return;
      }
      if (res.status === "current" || res.status === "downgraded" || res.status === "activated") {
        resetForm();
        await load();
        setNote(res.note || (res.status === "downgraded" ? "You are on Free." : `You are now on ${res.plan}.`));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start checkout");
    } finally {
      setBusy(false);
    }
  }

  const paidTarget = target === "pro" || target === "premium";

  return (
    <div>
      <PageTitle kicker="Account" title="Settings & plans" />
      <ErrorText error={error} />
      {note && <p className="mb-4 rounded-xl bg-sage/15 px-3 py-2 text-sm text-moss">{note}</p>}
      <p className="mb-4 max-w-2xl text-sm text-mist">
        Pro and Premium require a valid card (number, expiry, and security code). We check the card and never store the
        full number. Downgrading to Free still needs your account password.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        {PLANS.map((p) => (
          <Card key={p.id} className={usage?.plan === p.id ? "border-copper" : ""}>
            <div className="text-xs uppercase tracking-wider text-mist">{p.id}</div>
            <div className="font-display text-3xl">{p.price}</div>
            <p className="mt-2 text-sm text-mist">{p.note}</p>
            <Button
              className="mt-4"
              variant={usage?.plan === p.id ? "ink" : "copper"}
              onClick={() => {
                if (usage?.plan === p.id) return;
                setTarget(p.id);
                setPassword("");
                setNote("");
                setError("");
              }}
            >
              {usage?.plan === p.id ? "Current plan" : p.id === "free" ? "Downgrade" : "Subscribe"}
            </Button>
          </Card>
        ))}
      </div>

      {target === "free" && (
        <Card className="mt-6 space-y-3">
          <h2 className="font-display text-2xl">Confirm downgrade</h2>
          <p className="text-sm text-mist">Enter the password for this account to return to Free.</p>
          <form onSubmit={startCheckout} className="max-w-md space-y-3">
            <Field label="Account password">
              <PasswordInput required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <div className="flex gap-2">
              <Button type="submit" disabled={busy}>
                {busy ? "Checking…" : "Confirm downgrade"}
              </Button>
              <Button variant="ghost" onClick={resetForm}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      {paidTarget && (
        <Card className="mt-6 space-y-3">
          <h2 className="font-display text-2xl">Pay with card · {target}</h2>
          <p className="text-sm text-mist">
            Enter a valid card to activate {target}. Invalid numbers are rejected. We keep only the last four digits.
          </p>
          <form onSubmit={startCheckout} className="max-w-md space-y-3">
            <Field label="Name on card">
              <input
                required
                autoComplete="cc-name"
                className={inputClass}
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
              />
            </Field>
            <Field label="Card number">
              <input
                required
                inputMode="numeric"
                autoComplete="cc-number"
                placeholder="ACCT-000015"
                className={inputClass}
                value={cardNumber}
                onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Expiry (MM/YY)">
                <input
                  required
                  inputMode="numeric"
                  autoComplete="cc-exp"
                  placeholder="12/28"
                  className={inputClass}
                  value={exp}
                  onChange={(e) => setExp(formatExpiry(e.target.value))}
                />
              </Field>
              <Field label="CVC">
                <input
                  required
                  inputMode="numeric"
                  autoComplete="cc-csc"
                  placeholder="123"
                  maxLength={4}
                  className={inputClass}
                  value={cvc}
                  onChange={(e) => setCvc(e.target.value.replace(/\D/g, "").slice(0, 4))}
                />
              </Field>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={busy}>
                {busy ? "Checking card…" : `Activate ${target}`}
              </Button>
              <Button variant="ghost" onClick={resetForm}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      {usage && (
        <Card className="mt-6">
          <h2 className="font-display text-2xl">This month</h2>
          {usage.card_last4 ? (
            <p className="mt-2 text-sm text-mist">
              Card on file: {(usage.card_brand || "card").replace(/^./, (c) => c.toUpperCase())} ending in {usage.card_last4}
            </p>
          ) : null}
          <ul className="mt-3 space-y-1 text-sm">
            {(["resume_generations", "resume_analyses", "tailorings", "mock_interviews", "interview_questions", "cover_letters"] as const).map(
              (k) => (
                <li key={k}>
                  {k.replace(/_/g, " ")}: {usage[k].used} / {usage[k].limit}
                </li>
              )
            )}
          </ul>
          <p className="mt-3 text-xs text-mist">
            Voice interviews: {usage.voice_interviews ? "included" : "Premium"} · Models: {(usage.providers || []).join(", ") || "demo"}
          </p>
        </Card>
      )}
      <Card className="mt-4 space-y-3">
        <h2 className="font-display text-2xl">Privacy</h2>
        <p className="text-sm text-mist">
          You can export or delete your profile, documents, and AI memory. Model calls go through the backend only. See the{" "}
          <a href="/privacy" className="text-copper">
            privacy note
          </a>{" "}
          and{" "}
          <a href="/terms" className="text-copper">
            terms
          </a>
          .
        </p>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            onClick={async () => {
              const data = await api("/api/account/export");
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "career-coach-export.json";
              a.click();
            }}
          >
            Export my data
          </Button>
          <Button
            variant="ink"
            onClick={async () => {
              if (!confirm("Delete account and all data? This cannot be undone.")) return;
              await api("/api/account", { method: "DELETE" });
              clearSession();
              router.push("/");
            }}
          >
            Delete account
          </Button>
        </div>
      </Card>
    </div>
  );
}
