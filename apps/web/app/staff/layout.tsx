"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { StaffProvider, useStaff } from "@/lib/staff-context";
import {
  IconBell,
  IconClipboard,
  IconClose,
  IconFile,
  IconGrid,
  IconLogout,
  IconMenu,
  IconPackage,
  IconShield,
  IconSparkle,
  IconUsers,
} from "@/components/icons";

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

function StaffShell({ children, fullName }: { children: React.ReactNode; fullName: string }) {
  const { logout } = useAuth();
  const { position, unreadCount } = useStaff();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const nav = [
    { href: "/staff", label: "Overview", icon: IconGrid, badge: 0 },
    ...(position?.can_manage_staff ? [{ href: "/staff/team", label: "Team", icon: IconUsers, badge: 0 }] : []),
    ...(position?.can_manage_products
      ? [{ href: "/staff/products", label: "Products", icon: IconPackage, badge: 0 }]
      : []),
    ...(position?.can_manage_products
      ? [{ href: "/staff/policies", label: "Policies", icon: IconShield, badge: 0 }]
      : []),
    { href: "/staff/applications", label: "Applications", icon: IconFile, badge: 0 },
    ...(position?.can_manage_staff && position?.can_manage_products
      ? [{ href: "/staff/audit", label: "Audit", icon: IconClipboard, badge: 0 }]
      : []),
    { href: "/staff/notifications", label: "Notifications", icon: IconBell, badge: unreadCount },
  ];

  return (
    <div className="min-h-screen bg-slate-50 lg:flex print:block print:bg-white">
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden print:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-600 text-white">
            <IconSparkle className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">Bank Portal</span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/staff/notifications"
            className="relative rounded-md border border-slate-200 p-1.5 text-slate-600"
            aria-label="Notifications"
          >
            <IconBell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
                {unreadCount}
              </span>
            )}
          </Link>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="rounded-md border border-slate-200 p-1.5 text-slate-600"
            aria-label="Toggle navigation"
          >
            {menuOpen ? <IconClose className="h-5 w-5" /> : <IconMenu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Sidebar */}
      <aside
        className={`${
          menuOpen ? "block" : "hidden"
        } lg:flex lg:sticky lg:top-0 lg:h-screen w-full lg:w-64 shrink-0 flex-col border-b lg:border-b-0 lg:border-r border-slate-200 bg-white print:hidden`}
      >
        <div className="hidden items-center gap-2 px-6 py-5 lg:flex">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white">
            <IconSparkle className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">Bank Portal</p>
            <p className="text-[11px] text-slate-400">{position?.title ?? "Staff"}</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 px-3 py-3 lg:py-0">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active ? "bg-sky-50 text-sky-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <item.icon className={`h-5 w-5 ${active ? "text-sky-600" : "text-slate-400"}`} />
                  {item.label}
                </span>
                {item.badge > 0 && (
                  <span className="flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-semibold text-white">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-100 p-3">
          <div className="flex items-center gap-3 rounded-lg px-2 py-2">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sky-600 text-xs font-semibold text-white">
              {initials(fullName)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-900">{fullName}</p>
              <p className="truncate text-xs text-slate-400">{position?.title ?? "No position assigned"}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-1 flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
          >
            <IconLogout className="h-5 w-5" />
            Log out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-10 print:p-0">
        <div className="mx-auto max-w-6xl print:max-w-none">{children}</div>
      </main>
    </div>
  );
}

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || user.role !== "staff")) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user || user.role !== "staff") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-400">
        Loading...
      </div>
    );
  }

  return (
    <StaffProvider>
      <StaffShell fullName={user.full_name}>{children}</StaffShell>
    </StaffProvider>
  );
}
