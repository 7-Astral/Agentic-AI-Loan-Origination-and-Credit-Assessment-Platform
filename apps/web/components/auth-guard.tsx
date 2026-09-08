"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useParams, useRouter } from "next/navigation";

import { getStoredUser, roleHomePath } from "@/lib/auth";
import type { UserRole } from "@/lib/types/auth";

type GuardState = "checking" | "authorized";

/** Client-side route protection, not Next.js edge `middleware.ts` — the token lives in
 * localStorage (see lib/auth.ts), which middleware can't read. Redirects an unauthenticated
 * visitor to login, and an authenticated visitor on the wrong portal to the one their role
 * actually owns, rather than rendering that portal's content for them. */
export function AuthGuard({
  allowedRoles,
  children,
}: {
  allowedRoles: UserRole[];
  children: ReactNode;
}) {
  const router = useRouter();
  const params = useParams<{ bankSlug: string }>();
  const [state, setState] = useState<GuardState>("checking");

  useEffect(() => {
    const user = getStoredUser();
    if (!user) {
      router.replace(`/${params.bankSlug}/login`);
      return;
    }
    if (!allowedRoles.includes(user.role)) {
      router.replace(roleHomePath(user.role, params.bankSlug));
      return;
    }
    setState("authorized");
    // allowedRoles is passed as an inline array literal at every call site, so it isn't a
    // stable dependency — re-running this check on every render is unnecessary since only
    // params.bankSlug can actually change the outcome.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.bankSlug, router]);

  if (state === "checking") {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Loading...
      </div>
    );
  }

  return <>{children}</>;
}
