"use client";

import Link from "next/link";
import { AuthForm, Field, inputClass } from "@/components/ui";
import { BrandMark, TiltCard } from "@/components/pastel";
import { api } from "@/lib/api";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [done, setDone] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  return (
    <div className="grid min-h-screen place-items-center px-5 py-16">
      <TiltCard>
        <BrandMark />
        <div className="mt-7">
          {done ? (
            <div>
              <h1 className="font-display text-[27px] text-ink">Check your email</h1>
              <p className="mt-2 text-[13px] text-mist">{done}</p>
              {resetUrl ? (
                <p className="mt-4 text-sm">
                  <Link href={resetUrl} className="text-copper">
                    Open reset link
                  </Link>
                </p>
              ) : null}
            </div>
          ) : (
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
          )}
        </div>
        <p className="mt-4 text-center text-xs text-mist">
          <Link href="/login" className="text-copper">
            Back to sign in
          </Link>
        </p>
      </TiltCard>
    </div>
  );
}
