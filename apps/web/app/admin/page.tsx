"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type DashboardStats, ApiError } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { IconFile, IconGrid, IconPackage, IconUsers } from "@/components/icons";

const CARDS: { key: keyof DashboardStats; label: string; icon: typeof IconUsers; tone: string }[] = [
  { key: "total_users", label: "Users", icon: IconUsers, tone: "bg-indigo-50 text-indigo-600" },
  { key: "total_banks", label: "Banks", icon: IconGrid, tone: "bg-violet-50 text-violet-600" },
  { key: "total_loan_products", label: "Loan products", icon: IconPackage, tone: "bg-emerald-50 text-emerald-600" },
  { key: "total_applications", label: "Applications", icon: IconFile, tone: "bg-amber-50 text-amber-600" },
];

export default function AdminOverview() {
  const { token, user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .dashboard(token)
      .then(setStats)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, [token]);

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
        Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
      </h1>
      <p className="mt-1 text-sm text-slate-500">Platform-wide counts, pulled live from the database.</p>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {CARDS.map((c) => (
          <Card key={c.key} className="p-5">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${c.tone}`}>
              <c.icon className="h-5 w-5" />
            </div>
            <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">{c.label}</p>
            {stats ? (
              <p className="mt-1 text-3xl font-semibold text-slate-900">{stats[c.key]}</p>
            ) : (
              <Skeleton className="mt-2 h-8 w-16" />
            )}
          </Card>
        ))}
      </div>

      <Card className="mt-6 p-5">
        <h2 className="text-sm font-semibold text-slate-900">Getting started</h2>
        <p className="mt-1 text-sm text-slate-500">
          Add bank staff from the <span className="font-medium text-slate-700">Users</span> page, review
          product terms under <span className="font-medium text-slate-700">Products</span>, and tune
          auto-approval thresholds in <span className="font-medium text-slate-700">Policies</span>. Every
          admin action here is recorded in the <span className="font-medium text-slate-700">Audit</span> log.
        </p>
      </Card>
    </div>
  );
}
