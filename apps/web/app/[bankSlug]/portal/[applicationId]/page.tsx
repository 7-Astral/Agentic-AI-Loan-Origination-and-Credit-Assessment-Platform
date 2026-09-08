"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, Info, Loader2 } from "lucide-react";

import { AuthGuard } from "@/components/auth-guard";
import { Badge } from "@/components/ui/badge";
import { ApiError, getApplication } from "@/lib/api";
import {
  outcomeBadgeVariant,
  outcomeLabel,
  statusBadgeVariant,
  statusLabel,
} from "@/lib/application-status";
import type { ApplicationDetail } from "@/lib/types/application";

type PageState = "loading" | "not-found" | "error" | "ready";

export default function CustomerApplicationDetailPage() {
  return (
    <AuthGuard allowedRoles={["customer"]}>
      <CustomerApplicationDetailContent />
    </AuthGuard>
  );
}

function CustomerApplicationDetailContent() {
  const { bankSlug, applicationId } = useParams<{ bankSlug: string; applicationId: string }>();
  const [pageState, setPageState] = useState<PageState>("loading");
  const [application, setApplication] = useState<ApplicationDetail | null>(null);

  useEffect(() => {
    let cancelled = false;

    getApplication(applicationId)
      .then((result) => {
        if (cancelled) return;
        setApplication(result);
        setPageState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        // A 403 here means the id belongs to someone else's application — surfaced as
        // "not found" rather than an error, since a customer shouldn't learn whether the
        // id exists at all.
        setPageState(error instanceof ApiError && error.status === 403 ? "not-found" : "error");
      });

    return () => {
      cancelled = true;
    };
  }, [applicationId]);

  return (
    <div className="mx-auto w-full max-w-2xl p-4 sm:p-6">
      <Link
        href={`/${bankSlug}/portal`}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to your applications
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
        <div className="flex flex-col gap-4">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-lg font-semibold">{application.product_name}</h1>
            <Badge variant={statusBadgeVariant(application.status)} className="capitalize">
              {statusLabel(application.status)}
            </Badge>
          </header>

          <div className="rounded-lg border border-border p-4">
            <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Loan amount</dt>
                <dd className="font-medium">${Number(application.loan_amount).toLocaleString()}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Loan term</dt>
                <dd className="font-medium">{application.loan_term_months} months</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Purpose</dt>
                <dd className="font-medium">{application.purpose ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Submitted</dt>
                <dd className="font-medium">
                  {new Date(application.created_at).toLocaleDateString()}
                </dd>
              </div>
            </dl>
          </div>

          {application.outcome && (
            <div className="rounded-lg border border-border p-4">
              <p className="mb-2 text-sm font-semibold">Decision</p>
              <Badge variant={outcomeBadgeVariant(application.outcome)}>
                {outcomeLabel(application.outcome)}
              </Badge>
            </div>
          )}

          {application.info_request_message && (
            <div className="flex gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-900/20">
              <Info
                className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400"
                aria-hidden="true"
              />
              <div>
                <p className="font-semibold">More information requested</p>
                <p className="mt-1 text-muted-foreground">{application.info_request_message}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
