"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AuthForm, Field, PasswordInput } from "@/components/ui";
import { api } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";

  if (!token) {
    return (
      <div className="max-w-md">
        <h1 className="font-display text-4xl">Reset link missing</h1>
        <p className="mt-3 text-mist">Request a new password reset from the sign-in page.</p>
        <p className="mt-6 text-sm">
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
    <div className="grid min-h-screen place-items-center bg-paper px-6 paper-grid">
      <div>
        <Link href="/login" className="mb-3 inline-flex items-center text-sm text-mist hover:text-ink">
          ← Back
        </Link>
        <Link href="/" className="mb-10 block font-display text-2xl">
          Atelier
        </Link>
        <Suspense fallback={<p className="text-mist">Loading…</p>}>
          <ResetForm />
        </Suspense>
        <p className="mt-6 text-sm text-mist">
          <Link href="/login" className="text-copper">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
