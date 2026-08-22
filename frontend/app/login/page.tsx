"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm, Field, PasswordInput, inputClass } from "@/components/ui";
import { api, setSession } from "@/lib/api";

export default function LoginPage() {
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
          title="Welcome back"
          subtitle="Your profile, memory, and interview history are still here."
          submitLabel="Sign in"
          extra={
            <>
              <Field label="Email">
                <input name="email" type="email" required className={inputClass} />
              </Field>
              <Field label="Password">
                <PasswordInput name="password" required autoComplete="current-password" />
              </Field>
            </>
          }
          onSubmit={async (fd) => {
            const data = await api<{ access_token: string; user: unknown }>("/api/auth/login", {
              method: "POST",
              body: JSON.stringify({ email: fd.get("email"), password: fd.get("password") }),
            });
            setSession(data.access_token, data.user);
            router.push("/app");
          }}
        />
        <p className="mt-6 text-sm text-mist">
          <Link href="/forgot-password" className="text-copper">
            Forgot password?
          </Link>
        </p>
        <p className="mt-3 text-sm text-mist">
          New here?{" "}
          <Link href="/signup" className="text-copper">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
