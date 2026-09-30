"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api, type LoanApplicationOut } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconArrowRight, IconFile, IconLogout, IconSparkle } from "@/components/icons";

const STATUS_TONE: Record<string, "slate" | "indigo" | "emerald" | "amber" | "red"> = {
  draft: "slate",
  submitted: "slate",
  under_review: "amber",
  approved: "emerald",
  rejected: "red",
  disbursed: "indigo",
};

function statusLabel(status: string) {
  return status
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export default function CustomerPortal() {
  const { user, token, loading, logout } = useAuth();
  const router = useRouter();

  const [applications, setApplications] = useState<LoanApplicationOut[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);

  useEffect(() => {
    if (!loading && (!user || user.role !== "customer")) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!token) return;
    setAppsLoading(true);
    api
      .myApplications(token)
      .then(setApplications)
      .catch(() => {})
      .finally(() => setAppsLoading(false));
  }, [token]);

  if (loading || !user) return null;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:py-10">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <IconSparkle className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-slate-900">
                Welcome, {user.full_name.split(" ")[0]}
              </h1>
              <p className="text-xs text-slate-400">{user.email}</p>
            </div>
          </div>
          <Button variant="secondary" onClick={logout}>
            <IconLogout className="h-4 w-4" />
            Log out
          </Button>
        </div>

        <Card className="mt-8 flex flex-col items-start gap-4 border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <IconSparkle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Ready to apply for a loan?</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Our loan assistant asks the questions one at a time, checks your documents, and submits the
                application for you when you&apos;re ready.
              </p>
            </div>
          </div>
          <Link href="/customer/chat" className="shrink-0">
            <Button>
              Start application
              <IconArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </Card>

        <Card className="mt-6 overflow-hidden">
          <CardHeader title="My applications" subtitle={`${applications.length} total`} />
          {appsLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : applications.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
              <IconFile className="h-8 w-8 text-slate-300" />
              <p className="text-sm text-slate-400">No applications yet — start a chat above to apply.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {applications.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-2 px-5 py-4">
                  <div>
                    <span className="text-sm font-medium capitalize text-slate-900">{a.loan_type} loan</span>
                    <p className="mt-1 text-sm text-slate-500">${a.requested_amount.toLocaleString()}</p>
                    {a.pending_position_title && (
                      <p className="mt-0.5 text-xs text-slate-400">Pending {a.pending_position_title} approval</p>
                    )}
                    <p className="mt-1 text-xs text-slate-400">{new Date(a.created_at).toLocaleDateString()}</p>
                  </div>
                  <Badge tone={STATUS_TONE[a.status] ?? "slate"}>{statusLabel(a.status)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </main>
  );
}
