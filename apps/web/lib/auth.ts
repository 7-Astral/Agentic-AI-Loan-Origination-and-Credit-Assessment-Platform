import type { AuthenticatedUser } from "@/lib/types/auth";

// Dev-stage trade-off, documented in CLAUDE.md: the token lives in localStorage rather
// than an httpOnly cookie, which trades away XSS resistance for avoiding a CSRF story and
// `credentials: "include"` on every fetch. One consequence lives here: Next.js edge
// `middleware.ts` cannot read localStorage, so route protection is a client-side guard
// (components/auth-guard.tsx) instead — see that file for the redirect logic this enables.
const STORAGE_KEY = "loan-origination:auth";

interface StoredAuth {
  token: string;
  user: AuthenticatedUser;
}

function readStorage(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return readStorage()?.token ?? null;
}

export function getStoredUser(): AuthenticatedUser | null {
  return readStorage()?.user ?? null;
}

export function setAuth(token: string, user: AuthenticatedUser): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user }));
}

export function clearAuth(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

/** Where a signed-in user's role belongs — used both to route after login and by
 * auth-guard.tsx to redirect an authenticated user off a portal that isn't theirs. */
export function roleHomePath(role: AuthenticatedUser["role"], bankSlug: string): string {
  if (role === "customer") return `/${bankSlug}/portal`;
  if (role === "loan_officer" || role === "credit_manager") return `/${bankSlug}/officer`;
  return `/${bankSlug}/admin`;
}
