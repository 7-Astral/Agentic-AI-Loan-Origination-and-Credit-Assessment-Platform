"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  IconBuilding,
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

const NAV = [
  { href: "/admin", label: "Overview", icon: IconGrid },
  { href: "/admin/banks", label: "Banks", icon: IconBuilding },
  { href: "/admin/users", label: "Users", icon: IconUsers },
  { href: "/admin/products", label: "Products", icon: IconPackage },
  { href: "/admin/policies", label: "Policies", icon: IconShield },
  { href: "/admin/audit", label: "Audit", icon: IconFile },
];

function initials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  if (loading || !user || user.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-400">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <IconSparkle className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">Admin</span>
        </div>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="rounded-md border border-slate-200 p-1.5 text-slate-600"
          aria-label="Toggle navigation"
        >
          {menuOpen ? <IconClose className="h-5 w-5" /> : <IconMenu className="h-5 w-5" />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`${
          menuOpen ? "block" : "hidden"
        } lg:flex lg:sticky lg:top-0 lg:h-screen w-full lg:w-64 shrink-0 flex-col border-b lg:border-b-0 lg:border-r border-slate-200 bg-white`}
      >
        <div className="hidden items-center gap-2 px-6 py-5 lg:flex">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <IconSparkle className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">Admin Portal</p>
            <p className="text-[11px] text-slate-400">Loan Origination</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 px-3 py-3 lg:py-0">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <item.icon className={`h-5 w-5 ${active ? "text-indigo-600" : "text-slate-400"}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-100 p-3">
          <div className="flex items-center gap-3 rounded-lg px-2 py-2">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
              {initials(user.full_name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-900">{user.full_name}</p>
              <p className="truncate text-xs text-slate-400">{user.email}</p>
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

      <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-10">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
