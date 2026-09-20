"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { AuthShell } from "@/components/AuthShell";
import { Field, Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { IconAlert } from "@/components/icons";

const DEMO_ACCOUNTS = [
  { role: "Admin", email: "admin@bank.com", password: "Admin@123" },
  { role: "Credit Manager", email: "manager@bank.com", password: "Manager@123" },
  { role: "Loan Officer", email: "officer@bank.com", password: "Officer@123" },
  { role: "Customer", email: "customer@bank.com", password: "Customer@123" },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [expiredNotice, setExpiredNotice] = useState(false);

  // Read directly off window.location rather than useSearchParams (which
  // Next.js requires a Suspense boundary for) — this page is client-only
  // anyway, and this is a one-time check on mount, not something that
  // needs to react to client-side navigation.
  useEffect(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("expired")) {
      setExpiredNotice(true);
    }
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(email, password);
      if (user.role === "admin") router.push("/admin");
      else if (user.role === "staff") router.push("/staff");
      else router.push("/customer");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Is the API running?");
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemo(email: string, password: string) {
    setEmail(email);
    setPassword(password);
  }

  return (
    <AuthShell>
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in to your account to continue.</p>
      </div>

      {expiredNotice && (
        <div className="mt-5 flex items-start gap-2 rounded-lg bg-amber-50 px-3.5 py-2.5 text-sm text-amber-800">
          <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Your session expired — sign in again to continue.</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <Field label="Email">
          <Input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@bank.com"
            autoComplete="email"
          />
        </Field>
        <Field label="Password">
          <Input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </Field>

        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
            <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Button type="submit" loading={submitting} className="w-full">
          {submitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
          Register
        </Link>
      </p>

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-4">
        <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Demo accounts</p>
        <ul className="space-y-1.5">
          {DEMO_ACCOUNTS.map((acc) => (
            <li key={acc.email}>
              <button
                type="button"
                onClick={() => fillDemo(acc.email, acc.password)}
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-xs text-slate-500 transition-colors hover:bg-slate-50"
              >
                <span className="font-medium text-slate-600">{acc.role}</span>
                <span className="font-mono">{acc.email}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-2 px-2 text-[11px] text-slate-400">Click one to autofill · run the seed script first</p>
      </div>
    </AuthShell>
  );
}
