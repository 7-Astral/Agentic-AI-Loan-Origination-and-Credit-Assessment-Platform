"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, Loader2 } from "lucide-react";

import { RiskReportView } from "@/components/risk-report";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError, getApplication, postApplicationAction } from "@/lib/api";
import { statusBadgeVariant, statusLabel } from "@/lib/application-status";
import type { ApplicationDetail, OfficerActionType } from "@/lib/types/application";

type PageState = "loading" | "not-found" | "error" | "ready";

const ACTIONS: { action: OfficerActionType; label: string; variant: "default" | "outline" }[] = [
  { action: "approve", label: "Approve", variant: "default" },
  { action: "request_info", label: "Request more information", variant: "outline" },
  { action: "reject", label: "Reject", variant: "outline" },
  { action: "override", label: "Override", variant: "outline" },
];

const REASON_REQUIRED: OfficerActionType[] = ["reject", "override"];

/** Shared by the officer detail page (full read/write access to its own bank's
 * applications) and the admin detail page (read-only oversight across every bank) — the
 * backend already enforces who can act via `POST /applications/{id}/actions`'s
 * `require_role`, so `canAct` here only controls whether the action UI renders at all,
 * not a second, independent permission check. */
export function ApplicationDetailView({
  applicationId,
  backHref,
  backLabel,
  canAct,
}: {
  applicationId: string;
  backHref: string;
  backLabel: string;
  canAct: boolean;
}) {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [pendingAction, setPendingAction] = useState<OfficerActionType | null>(null);
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setPageState("loading");
      try {
        const result = await getApplication(applicationId);
        if (cancelled) return;
        setApplication(result);
        setPageState("ready");
      } catch (error) {
        if (cancelled) return;
        setPageState(error instanceof ApiError && error.status === 403 ? "not-found" : "error");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [applicationId]);

  async function submitAction(action: OfficerActionType) {
    if (REASON_REQUIRED.includes(action) && reason.trim().length === 0) {
      setActionError("A reason is required for this action.");
      return;
    }

    setPendingAction(action);
    setActionError(null);
    try {
      const result = await postApplicationAction(applicationId, {
        action,
        reason: reason.trim().length > 0 ? reason.trim() : null,
      });
      setApplication(result);
      setReason("");
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Couldn't record that action.");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <Link
        href={backHref}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        {backLabel}
      </Link>

      {pageState === "loading" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          <p className="text-sm">Loading application...</p>
        </div>
      )}

      {pageState === "not-found" && (
        <div className="rounded-lg border border-border p-10 text-center">
          <p className="text-sm font-medium">This application couldn&apos;t be found.</p>
        </div>
      )}

      {pageState === "error" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center">
          <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
          <p className="text-sm font-medium">
            Couldn&apos;t load this application. Please try again.
          </p>
        </div>
      )}

      {pageState === "ready" && application && (
        <div className="flex flex-col gap-6">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-lg font-semibold">
                {application.customer_name} · {application.product_name}
              </h1>
              <p className="text-sm text-muted-foreground">
                ${Number(application.loan_amount).toLocaleString()} over{" "}
                {application.loan_term_months} months
                {application.purpose ? ` · ${application.purpose}` : ""}
              </p>
            </div>
            <Badge variant={statusBadgeVariant(application.status)} className="capitalize">
              {statusLabel(application.status)}
            </Badge>
          </header>

          {application.customer_profile && (
            <div className="rounded-lg border border-border p-4">
              <h2 className="mb-3 font-semibold">Customer profile</h2>
              <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Employment status</dt>
                  <dd className="font-medium">
                    {application.customer_profile.employment_status ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Income</dt>
                  <dd className="font-medium">
                    {application.customer_profile.income
                      ? `$${Number(application.customer_profile.income).toLocaleString()}`
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Monthly expenses</dt>
                  <dd className="font-medium">
                    {application.customer_profile.expenses
                      ? `$${Number(application.customer_profile.expenses).toLocaleString()}`
                      : "—"}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {application.risk_report && (
            <div>
              <h2 className="mb-3 font-semibold">Risk assessment</h2>
              <RiskReportView report={application.risk_report} />
            </div>
          )}

          <div className="rounded-lg border border-border p-4">
            <h2 className="mb-3 font-semibold">Action history</h2>
            {application.actions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No actions have been recorded yet.</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {application.actions.map((action) => (
                  <li key={action.id} className="text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium capitalize">
                        {action.action.replace(/_/g, " ")}
                      </span>
                      <span className="text-muted-foreground">
                        by {action.officer_name} · {new Date(action.created_at).toLocaleString()}
                      </span>
                    </div>
                    {action.reason && <p className="mt-1 text-muted-foreground">{action.reason}</p>}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {canAct && application.status !== "decided" && (
            <div className="rounded-lg border border-border p-4">
              <h2 className="mb-3 font-semibold">Take action</h2>

              <div className="mb-3 flex flex-col gap-1.5">
                <label htmlFor="reason" className="text-sm font-medium">
                  Reason{" "}
                  <span className="font-normal text-muted-foreground">
                    (required for reject and override)
                  </span>
                </label>
                <textarea
                  id="reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  rows={3}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  placeholder="Explain the reason for this decision..."
                />
              </div>

              {actionError && (
                <div className="mb-3 flex items-start gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{actionError}</span>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                {ACTIONS.map((item) => (
                  <Button
                    key={item.action}
                    type="button"
                    variant={item.variant}
                    disabled={pendingAction !== null}
                    onClick={() => void submitAction(item.action)}
                  >
                    {pendingAction === item.action && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    )}
                    {item.label}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
