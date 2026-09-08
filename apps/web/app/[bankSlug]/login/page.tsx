"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertTriangle, Landmark, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, getBank, login, register } from "@/lib/api";
import { roleHomePath, setAuth } from "@/lib/auth";
import type { Bank } from "@/lib/types/bank";
import { hexToHslTriplet } from "@/lib/utils";

type Mode = "sign-in" | "register";
type PageState = "loading" | "not-found" | "error" | "ready";

export default function LoginPage() {
  const { bankSlug } = useParams<{ bankSlug: string }>();
  const router = useRouter();

  const [pageState, setPageState] = useState<PageState>("loading");
  const [bank, setBank] = useState<Bank | null>(null);

  const [mode, setMode] = useState<Mode>("sign-in");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getBank(bankSlug)
      .then((result) => {
        if (cancelled) return;
        if (!result) {
          setPageState("not-found");
          return;
        }
        setBank(result);
        setPageState("ready");
      })
      .catch(() => {
        if (!cancelled) setPageState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [bankSlug]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting || !bank) return;
    setFormError(null);
    setIsSubmitting(true);

    try {
      const result =
        mode === "sign-in"
          ? await login(email, password)
          : await register({ name, email, password, bank_id: bank.id });
      setAuth(result.access_token, result.user);
      router.push(roleHomePath(result.user.role, bankSlug));
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "Something went wrong. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (pageState === "loading") {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (pageState === "not-found" || pageState === "error" || !bank) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <h1 className="text-xl font-semibold">We couldn&apos;t load this bank</h1>
        <p className="text-muted-foreground">Please check the link and try again.</p>
      </div>
    );
  }

  const themeStyle = {
    "--primary": hexToHslTriplet(bank.branding.primary_color),
  } as React.CSSProperties;

  return (
    <div className="flex flex-1 items-center justify-center p-4 sm:p-6" style={themeStyle}>
      <div className="w-full max-w-sm rounded-lg border border-border p-6 sm:p-8">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <Landmark className="h-6 w-6 text-primary" aria-hidden="true" />
          <h1 className="text-lg font-semibold">{bank.name}</h1>
          <p className="text-sm text-muted-foreground">
            {mode === "sign-in" ? "Sign in to your account" : "Create a customer account"}
          </p>
        </div>

        <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
          {mode === "register" && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="name" className="text-sm font-medium">
                Full name
              </label>
              <Input
                id="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                required
              />
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-sm font-medium">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-sm font-medium">
              Password
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
              minLength={mode === "register" ? 8 : undefined}
              required
            />
          </div>

          {formError && (
            <div className="flex items-start gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{formError}</span>
            </div>
          )}

          <Button type="submit" disabled={isSubmitting} className="mt-2">
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
            {mode === "sign-in" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          {mode === "sign-in" ? (
            <>
              Don&apos;t have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("register");
                  setFormError(null);
                }}
                className="font-medium text-primary hover:underline"
              >
                Register
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("sign-in");
                  setFormError(null);
                }}
                className="font-medium text-primary hover:underline"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
