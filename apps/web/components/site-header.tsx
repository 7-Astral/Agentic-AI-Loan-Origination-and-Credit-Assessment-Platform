"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Landmark, LogOut, Search, Settings, User } from "lucide-react";

import { Avatar } from "@/components/ui/avatar";
import { clearAuth, getStoredUser } from "@/lib/auth";
import type { AuthenticatedUser } from "@/lib/types/auth";
import { cn } from "@/lib/utils";

const NAV_LINKS: { label: string; href: string }[] = [
  { label: "Dashboard", href: "/" },
  { label: "Applications", href: "/applications" },
  { label: "Documents", href: "#" },
  { label: "Support", href: "#" },
];

/** Persistent top nav, rendered once from the root layout so it stays put across routes
 * (home, applications, applications detail, risk assessment) rather than being duplicated
 * — and re-mounted, losing its identity — per page. Deliberately uses the app's default
 * theme colour rather than any bank's branding, since it's global chrome, not page content. */
export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);

  // Re-read on every navigation (not just on mount) since this header is rendered once from
  // the root layout and never remounts — it wouldn't otherwise notice a login/logout that
  // happened via the localStorage-backed auth state elsewhere on the page.
  useEffect(() => {
    setUser(getStoredUser());
  }, [pathname]);

  function handleSignOut() {
    const bankSlug = pathname.split("/")[1] || "demo-mutual";
    clearAuth();
    setUser(null);
    router.push(`/${bankSlug}/login`);
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4 sm:h-16 sm:px-6">
      <div className="flex items-center gap-8">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-primary">
          <Landmark className="h-5 w-5" aria-hidden="true" />
          LendFlow AI
        </Link>
        <nav className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((link) => {
            const isActive = link.href !== "#" && pathname === link.href;
            return (
              <Link
                key={link.label}
                href={link.href}
                className={cn(
                  "border-b-2 border-transparent pb-0.5 text-sm",
                  isActive
                    ? "border-primary font-medium text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        <button
          type="button"
          aria-label="Search"
          className="hidden text-muted-foreground hover:text-foreground sm:block"
        >
          <Search className="h-5 w-5" />
        </button>
        <button
          type="button"
          aria-label="Notifications"
          className="hidden text-muted-foreground hover:text-foreground sm:block"
        >
          <Bell className="h-5 w-5" />
        </button>
        <button
          type="button"
          aria-label="Settings"
          className="hidden text-muted-foreground hover:text-foreground sm:block"
        >
          <Settings className="h-5 w-5" />
        </button>
        {user ? (
          <button
            type="button"
            onClick={handleSignOut}
            aria-label="Sign out"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">{user.name}</span>
          </button>
        ) : (
          <Avatar className="bg-secondary text-secondary-foreground">
            <User className="h-5 w-5" aria-hidden="true" />
          </Avatar>
        )}
      </div>
    </header>
  );
}
