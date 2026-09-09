"use client";

import Link from "next/link";
import { AlertTriangle, FileStack, ListTree, Package, Scale, ScrollText, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useAdminData } from "@/lib/mock/admin-store";
import { useBanks } from "@/lib/mock/banks-store";

export default function BankDashboardPage({ params }: { params: { bankId: string } }) {
  const { getBank } = useBanks();
  const bank = getBank(params.bankId)!;
  const { loanTypes, products, documentTypes, policyVersions, rules, auditLog } = useAdminData();
  const activePolicyVersion = policyVersions.find((v) => v.status === "active");

  const categoryCount = loanTypes.reduce((sum, lt) => sum + lt.categories.length, 0);

  const stats = [
    {
      label: "Loan types",
      value: loanTypes.length,
      sub: `${categoryCount} categories`,
      icon: ListTree,
      href: "loan-types",
    },
    { label: "Products", value: products.length, sub: "across all categories", icon: Package, href: "products" },
    {
      label: "Document types",
      value: documentTypes.length,
      sub: "in requirement matrix",
      icon: FileStack,
      href: "documents",
    },
    {
      label: "Policy version",
      value: activePolicyVersion?.version ?? "—",
      sub: `${policyVersions.length} version${policyVersions.length === 1 ? "" : "s"} total`,
      icon: ShieldCheck,
      href: "policy",
    },
    { label: "Assessment rules", value: rules.length, sub: "individual + business", icon: Scale, href: "rules" },
    {
      label: "Audit events",
      value: auditLog.length,
      sub: `${auditLog.filter((e) => e.type === "llm_call").length} LLM calls logged`,
      icon: ScrollText,
      href: "audit",
    },
  ];

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-10">
      <div className="mb-8 flex items-center gap-3">
        <span
          className="h-3 w-3 shrink-0 rounded-full"
          style={{ backgroundColor: bank.primaryColor }}
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{bank.name}</h1>
          <p className="text-sm text-muted-foreground">Overview of this bank&apos;s configuration.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {stats.map((stat) => (
          <Link
            key={stat.label}
            href={`/admin/banks/${params.bankId}/${stat.href}`}
            className="group rounded-xl border border-border bg-background p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md"
          >
            <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <stat.icon className="h-4.5 w-4.5" aria-hidden="true" />
            </span>
            <p className="text-2xl font-semibold tabular-nums">{stat.value}</p>
            <p className="text-sm font-medium">{stat.label}</p>
            <p className="text-xs text-muted-foreground">{stat.sub}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
