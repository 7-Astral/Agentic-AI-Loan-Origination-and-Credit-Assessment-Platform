"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { listBankApplications } from "@/lib/api";
import type { ApplicationSummary } from "@/lib/types/report";
import { cn } from "@/lib/utils";

const TIER_BADGE: Record<string, string> = {
  auto_eligible: "bg-emerald-600 text-white hover:bg-emerald-600",
  underwriter_review: "bg-amber-500 text-white hover:bg-amber-500",
  decline_recommended: "bg-red-600 text-white hover:bg-red-600",
};

const TIER_LABEL: Record<string, string> = {
  auto_eligible: "Auto-eligible",
  underwriter_review: "Underwriter review",
  decline_recommended: "Decline recommended",
};

function TierBadge({ tier }: { tier: string | null }) {
  if (!tier) {
    return <Badge variant="outline">Not scored</Badge>;
  }
  return <Badge className={TIER_BADGE[tier] ?? ""}>{TIER_LABEL[tier] ?? tier}</Badge>;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function ApplicationsPage({ params }: { params: { bankId: string } }) {
  const router = useRouter();
  const [applications, setApplications] = useState<ApplicationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    listBankApplications(params.bankId)
      .then((data) => setApplications(data.applications))
      .catch((err: Error) => setError(err.message));
  }, [params.bankId]);

  useEffect(load, [load]);

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Applications</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every application submitted for this bank, with its weighted 5C score and recommended
          decision tier. Click through for the full credit assessment report.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {applications === null && !error && (
        <p className="p-6 text-sm text-muted-foreground">Loading…</p>
      )}

      {applications !== null && applications.length === 0 && (
        <div className="rounded-xl border border-dashed border-input bg-background py-16 text-center text-sm text-muted-foreground">
          No applications yet for this bank.
        </div>
      )}

      {applications !== null && applications.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border shadow-sm">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-3 font-medium">Application</th>
                <th className="px-4 py-3 font-medium">Product</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Overall score</th>
                <th className="px-4 py-3 font-medium">Tier</th>
                <th className="px-4 py-3 font-medium">Last updated</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((application, index) => (
                <tr
                  key={application.session_id}
                  onClick={() => router.push(`/admin/banks/${params.bankId}/applications/${application.session_id}`)}
                  className={cn(
                    "cursor-pointer border-b border-border last:border-0 hover:bg-secondary/30",
                    index % 2 === 1 && "bg-secondary/10",
                  )}
                >
                  <td className="px-4 py-3">
                    <p className="font-medium">{application.session_id.slice(0, 8)}&hellip;</p>
                  </td>
                  <td className="px-4 py-3">{application.product_code ?? "—"}</td>
                  <td className="px-4 py-3 capitalize">{application.status.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3">
                    {application.overall_score !== null ? (
                      <div className="flex items-center gap-2">
                        <Progress value={application.overall_score} className="w-24" />
                        <span className="tabular-nums text-xs text-muted-foreground">
                          {application.overall_score.toFixed(0)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Not yet assessed</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <TierBadge tier={application.tier} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                    {formatDate(application.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
