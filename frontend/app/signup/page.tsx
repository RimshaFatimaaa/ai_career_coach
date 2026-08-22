"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm, Field, PasswordInput, inputClass } from "@/components/ui";
import { api, setSession } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  return (
    <div className="grid min-h-screen place-items-center bg-paper px-6 paper-grid">
      <div>
        <Link href="/" className="mb-3 inline-flex items-center text-sm text-mist hover:text-ink">
          ← Back
        </Link>
        <Link href="/" className="mb-10 block font-display text-2xl">
          Atelier
        </Link>
        <AuthForm
          title="Build it once"
          subtitle="A persistent career profile that powers coaching, resumes, and interviews."
          submitLabel="Create account"
          extra={
            <>
              <Field label="Full name">
                <input name="full_name" required className={inputClass} />
              </Field>
              <Field label="Email">
                <input name="email" type="email" required className={inputClass} />
              </Field>
              <Field label="Password (min 8)">
                <PasswordInput name="password" minLength={8} required autoComplete="new-password" />
              </Field>
              <label className="flex items-start gap-2 text-sm text-mist">
                <input name="accept_terms" type="checkbox" required className="mt-1" />
                <span>
                  I agree to the{" "}
                  <Link href="/terms" className="text-copper">
                    terms of service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className="text-copper">
                    privacy note
                  </Link>
                  .
                </span>
              </label>
            </>
          }
          onSubmit={async (fd) => {
            const data = await api<{ access_token: string; user: unknown }>("/api/auth/register", {
              method: "POST",
              body: JSON.stringify({
                full_name: fd.get("full_name"),
                email: fd.get("email"),
                password: fd.get("password"),
                accept_terms: fd.get("accept_terms") === "on",
              }),
            });
            setSession(data.access_token, data.user);
            router.push("/app/profile");
          }}
        />
        <p className="mt-6 text-sm text-mist">
          Already have an account?{" "}
          <Link href="/login" className="text-copper">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
