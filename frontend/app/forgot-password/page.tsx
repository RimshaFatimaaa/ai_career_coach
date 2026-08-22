"use client";

import Link from "next/link";
import { AuthForm, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [done, setDone] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  return (
    <div className="grid min-h-screen place-items-center bg-paper px-6 paper-grid">
      <div>
        <Link href="/login" className="mb-3 inline-flex items-center text-sm text-mist hover:text-ink">
          ← Back
        </Link>
        <Link href="/" className="mb-10 block font-display text-2xl">
          Atelier
        </Link>
        {done ? (
          <div className="max-w-md">
            <h1 className="font-display text-4xl">Check your email</h1>
            <p className="mt-3 text-mist">{done}</p>
            {resetUrl ? (
              <p className="mt-4 text-sm">
                <Link href={resetUrl} className="text-copper">
                  Open reset link
                </Link>
              </p>
            ) : null}
            <p className="mt-6 text-sm text-mist">
              <Link href="/login" className="text-copper">
                Back to sign in
              </Link>
            </p>
          </div>
        ) : (
          <>
            <AuthForm
              title="Forgot password"
              subtitle="We’ll send a reset link if that email has an account."
              submitLabel="Send reset link"
              extra={
                <Field label="Email">
                  <input name="email" type="email" required className={inputClass} />
                </Field>
              }
              onSubmit={async (fd) => {
                const res = await api<{ message: string; reset_url?: string }>("/api/auth/forgot-password", {
                  method: "POST",
                  body: JSON.stringify({ email: fd.get("email") }),
                });
                setDone(res.message);
                setResetUrl(res.reset_url || "");
              }}
            />
            <p className="mt-6 text-sm text-mist">
              <Link href="/login" className="text-copper">
                Back to sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
