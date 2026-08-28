"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AuthForm, Field, PasswordInput, inputClass } from "@/components/ui";
import { BrandMark, TiltCard } from "@/components/pastel";
import { api, setSession } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  return (
    <div className="relative grid min-h-screen place-items-center px-5 py-16">
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
        <div className="mt-7">
          <AuthForm
            title="Build it once"
            subtitle="A career profile that powers coaching, resumes, and interviews."
            submitLabel="Create account"
            extra={
              <>
                <Field label="Full name">
                  <input name="full_name" required className={inputClass} />
                </Field>
                <Field label="Email">
                  <input name="email" type="email" required className={inputClass} />
                </Field>
                <Field label="Password (min 8, needs a letter and a number)">
                  <PasswordInput name="password" minLength={8} required autoComplete="new-password" />
                </Field>
                <label className="flex items-start gap-2 text-xs text-mist">
                  <input name="accept_terms" type="checkbox" required className="mt-0.5" />
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
        </div>
        <p className="mt-4 text-center text-xs text-mist">
          Already have an account?{" "}
          <Link href="/login" className="text-copper">
            Sign in
          </Link>
        </p>
      </TiltCard>
    </div>
  );
}
