"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AuthForm, Field, PasswordInput } from "@/components/ui";
import { BrandMark, TiltCard } from "@/components/pastel";
import { api } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";

  if (!token) {
    return (
      <div>
        <h1 className="font-display text-[27px] text-ink">Reset link missing</h1>
        <p className="mt-2 text-[13px] text-mist">Request a new password reset from the sign-in page.</p>
        <p className="mt-4 text-sm">
          <Link href="/forgot-password" className="text-copper">
            Forgot password
          </Link>
        </p>
      </div>
    );
  }

  return (
    <AuthForm
      title="Choose a new password"
      subtitle="This link works once and expires after an hour."
      submitLabel="Update password"
      extra={
        <Field label="New password (min 8)">
          <PasswordInput name="password" minLength={8} required autoComplete="new-password" />
        </Field>
      }
      onSubmit={async (fd) => {
        await api("/api/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({ token, password: fd.get("password") }),
        });
        router.push("/login");
      }}
    />
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="grid min-h-screen place-items-center px-5 py-16">
      <TiltCard>
        <BrandMark />
        <div className="mt-7">
          <Suspense fallback={<p className="text-mist">Loading…</p>}>
            <ResetForm />
          </Suspense>
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
