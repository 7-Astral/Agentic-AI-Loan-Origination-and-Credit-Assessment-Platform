"use client";

import Link from "next/link";
import { ChevronRight, Lock, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoanPolicyTable } from "@/components/admin/policy-version-view";
import { useAdminData } from "@/lib/mock/admin-store";

export default function PolicyPage({ params }: { params: { bankId: string } }) {
  const { policyVersions, loanTypes } = useAdminData();

  const active = policyVersions.find((v) => v.status === "active");
  const history = [...policyVersions].sort((a, b) => (a.effectiveFrom < b.effectiveFrom ? 1 : -1));

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Policy</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Versioned, per-loan-type eligibility policy age, residency, deposit/LVR, income and
            serviceability rules the assessment engine relies on.
          </p>
        </div>
        <Link href={`/admin/banks/${params.bankId}/policy/new`}>
          <Button>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            New version
          </Button>
        </Link>
      </div>

      {active && (
        <section className="mb-10">
          <div className="mb-4 flex items-center gap-3">
            <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">Active</Badge>
            <h2 className="font-semibold">{active.version}</h2>
            <span className="text-sm text-muted-foreground">effective {active.effectiveFrom}</span>
          </div>
          {active.notes && <p className="mb-4 text-sm text-muted-foreground">{active.notes}</p>}

          <div className="mb-6 flex gap-3 rounded-lg border border-input bg-secondary/30 p-3 text-xs text-muted-foreground">
            <Lock className="h-3.5 w-3.5 shrink-0 translate-y-0.5" aria-hidden="true" />
            <p>
              Policy versions are immutable, this is read-only.
            </p>
          </div>

          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Loan policy
          </h3>
          <LoanPolicyTable rows={active.loanPolicyRows} loanTypes={loanTypes} />
        </section>
      )}

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Version history
        </h2>
        <div className="divide-y divide-border rounded-xl border border-border bg-background shadow-sm">
          {history.map((version) => (
            <Link
              key={version.id}
              href={`/admin/banks/${params.bankId}/policy/${version.id}`}
              className="flex items-center justify-between gap-4 p-4 transition-colors hover:bg-secondary/30"
            >
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium">{version.version}</p>
                  <Badge
                    variant={version.status === "active" ? "secondary" : "outline"}
                    className={version.status === "active" ? "text-emerald-700" : ""}
                  >
                    {version.status === "active" ? "Active" : "Superseded"}
                  </Badge>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Effective {version.effectiveFrom} · created {version.createdAt}
                </p>
              </div>
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
