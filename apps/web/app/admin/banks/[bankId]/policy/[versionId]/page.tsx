"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Copy, Lock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoanPolicyTable } from "@/components/admin/policy-version-view";
import { useAdminData } from "@/lib/mock/admin-store";

export default function PolicyVersionDetailPage({
  params,
}: {
  params: { bankId: string; versionId: string };
}) {
  const { policyVersions, loanTypes } = useAdminData();
  const version = policyVersions.find((v) => v.id === params.versionId);

  if (!version) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-10">
      <Link
        href={`/admin/banks/${params.bankId}/policy`}
        className="mb-6 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        All policy versions
      </Link>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Badge
            className={
              version.status === "active" ? "bg-emerald-600 text-white hover:bg-emerald-600" : ""
            }
            variant={version.status === "active" ? "default" : "outline"}
          >
            {version.status === "active" ? "Active" : "Superseded"}
          </Badge>
          <h1 className="text-2xl font-semibold tracking-tight">{version.version}</h1>
        </div>
        <Link href={`/admin/banks/${params.bankId}/policy/new?clone=${version.id}`}>
          <Button variant="outline">
            <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
            Clone as new version
          </Button>
        </Link>
      </div>

      <p className="mb-1 text-sm text-muted-foreground">
        Effective {version.effectiveFrom} · created {version.createdAt}
      </p>
      {version.notes && <p className="mb-4 text-sm text-muted-foreground">{version.notes}</p>}

      <div className="mb-6 flex gap-3 rounded-lg border border-input bg-secondary/30 p-3 text-xs text-muted-foreground">
        <Lock className="h-3.5 w-3.5 shrink-0 translate-y-0.5" aria-hidden="true" />
        <p>
          This is a frozen snapshot exactly as it was in effect. policy versions can never be edited
          after creation, only superseded by a new one.
        </p>
      </div>

      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Loan policy
      </h2>
      <LoanPolicyTable rows={version.loanPolicyRows} loanTypes={loanTypes} />
    </div>
  );
}
