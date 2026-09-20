"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useStaff } from "@/lib/staff-context";
import { api, type LoanApplicationOut, ApiError } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { IconBell, IconFile, IconShield, IconUsers } from "@/components/icons";

export default function StaffOverview() {
  const { user, token } = useAuth();
  const { position, unreadCount, loading: staffLoading } = useStaff();
  const [applications, setApplications] = useState<LoanApplicationOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .bankApplications(token)
      .then(setApplications)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, [token]);

  const pendingForMe =
    applications?.filter((a) => a.status === "under_review" && a.pending_position_title === position?.title)
      .length ?? 0;
  const totalPending = applications?.filter((a) => a.status === "under_review").length ?? 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
        Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        {staffLoading ? (
          "Loading your position..."
        ) : position ? (
          <>
            Signed in as <span className="font-medium text-slate-700">{position.title}</span> —{" "}
            {position.max_approval_amount
              ? `approve up to $${Number(position.max_approval_amount).toLocaleString()}`
              : "unlimited approval authority"}
            .
          </>
        ) : (
          "No position assigned yet — ask an admin or manager to set one so you can approve loans."
        )}
      </p>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
            <IconFile className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">Awaiting your approval</p>
          {applications ? (
            <p className="mt-1 text-3xl font-semibold text-slate-900">{pendingForMe}</p>
          ) : (
            <Skeleton className="mt-2 h-8 w-16" />
          )}
        </Card>
        <Card className="p-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-sky-600">
            <IconShield className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">Total under review</p>
          {applications ? (
            <p className="mt-1 text-3xl font-semibold text-slate-900">{totalPending}</p>
          ) : (
            <Skeleton className="mt-2 h-8 w-16" />
          )}
        </Card>
        <Card className="p-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-50 text-red-600">
            <IconBell className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">Unread notifications</p>
          <p className="mt-1 text-3xl font-semibold text-slate-900">{unreadCount}</p>
        </Card>
        <Card className="p-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
            <IconUsers className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">Your permissions</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone={position?.can_manage_staff ? "emerald" : "slate"}>
              {position?.can_manage_staff ? "Manages staff" : "No staff access"}
            </Badge>
            <Badge tone={position?.can_manage_products ? "emerald" : "slate"}>
              {position?.can_manage_products ? "Manages products" : "No product access"}
            </Badge>
          </div>
        </Card>
      </div>

      <Card className="mt-6 p-5">
        <h2 className="text-sm font-semibold text-slate-900">How approvals work</h2>
        <p className="mt-1 text-sm text-slate-500">
          Every application is checked against your bank&apos;s auto-approval policy first. If it exceeds the
          threshold, it&apos;s routed to the lowest position on your approval ladder whose limit covers the
          amount, and everyone holding that position is notified. Review escalated applications under{" "}
          <span className="font-medium text-slate-700">Applications</span>.
        </p>
      </Card>
    </div>
  );
}
