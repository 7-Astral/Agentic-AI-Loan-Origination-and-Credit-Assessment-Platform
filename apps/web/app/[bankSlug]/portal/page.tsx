"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, FileQuestion, Landmark, Loader2 } from "lucide-react";

import { AuthGuard } from "@/components/auth-guard";
import { Badge } from "@/components/ui/badge";
import { listApplications } from "@/lib/api";
import { statusBadgeVariant, statusLabel } from "@/lib/application-status";
import type { ApplicationSummary } from "@/lib/types/application";

type PageState = "loading" | "error" | "ready";

export default function CustomerPortalPage() {
  const { bankSlug } = useParams<{ bankSlug: string }>();

  return (
    <AuthGuard allowedRoles={["customer"]}>
      <CustomerPortalContent bankSlug={bankSlug} />
    </AuthGuard>
  );
}

function CustomerPortalContent({ bankSlug }: { bankSlug: string }) {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);

  useEffect(() => {
    let cancelled = false;

    listApplications()
      .then((result) => {
        if (cancelled) return;
        setApplications(result);
        setPageState("ready");
      })
      .catch(() => {
        if (!cancelled) setPageState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <header className="mb-6 flex items-center gap-2">
        <Landmark className="h-5 w-5 text-primary" aria-hidden="true" />
        <h1 className="text-lg font-semibold">Your applications</h1>
      </header>

      {pageState === "loading" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          <p className="text-sm">Loading your applications...</p>
        </div>
      )}

      {pageState === "error" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center">
          <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
          <p className="text-sm font-medium">
            Couldn&apos;t load your applications. Please try again.
          </p>
        </div>
      )}

      {pageState === "ready" && applications.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-10 text-center text-muted-foreground">
          <FileQuestion className="h-6 w-6" aria-hidden="true" />
          <p className="text-sm">You don&apos;t have any applications yet.</p>
          <Link href={`/${bankSlug}`} className="text-sm font-medium text-primary hover:underline">
            Start a new enquiry
          </Link>
        </div>
      )}

      {pageState === "ready" && applications.length > 0 && (
        <ul className="flex flex-col gap-2">
          {applications.map((application) => (
            <li
              key={application.id}
              className="rounded-lg border border-border transition-colors hover:border-primary"
            >
              <Link
                href={`/${bankSlug}/portal/${application.id}`}
                className="flex flex-wrap items-center justify-between gap-3 p-4 hover:bg-secondary/50"
              >
                <div className="flex flex-col gap-1">
                  <span className="font-medium">{application.product_name}</span>
                  <span className="text-xs text-muted-foreground">
                    ${Number(application.loan_amount).toLocaleString()} ·{" "}
                    {new Date(application.created_at).toLocaleDateString()}
                  </span>
                </div>
                <Badge variant={statusBadgeVariant(application.status)} className="capitalize">
                  {statusLabel(application.status)}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
