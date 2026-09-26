"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Banknote,
  Building2,
  CheckCircle2,
  FileText,
  MessageSquare,
  ShieldAlert,
  ShieldQuestion,
  Sparkles,
  TrendingUp,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { getApplicationReport } from "@/lib/api";
import type { ApplicationReport, FiveC, GroupScore } from "@/lib/types/report";
import { cn } from "@/lib/utils";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function formatFactValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString();
  return String(value).replace(/_/g, " ");
}

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

const RISK_BADGE: Record<string, string> = {
  low: "bg-emerald-600 text-white hover:bg-emerald-600",
  medium: "bg-amber-500 text-white hover:bg-amber-500",
  high: "bg-red-600 text-white hover:bg-red-600",
};

const RISK_FACTOR_DOT: Record<string, string> = {
  high: "bg-red-600",
  medium: "bg-amber-500",
  low: "bg-muted-foreground",
};

const FIVE_C_ORDER: FiveC[] = ["capacity", "capital", "character", "collateral", "conditions"];

const FIVE_C_META: Record<FiveC, { label: string; icon: typeof TrendingUp; blurb: string }> = {
  capacity: { label: "Capacity", icon: TrendingUp, blurb: "Ability to service the repayments" },
  capital: { label: "Capital", icon: Banknote, blurb: "Deposit, savings and net asset position" },
  character: { label: "Character", icon: UserCheck, blurb: "Credit history and repayment conduct" },
  collateral: { label: "Collateral", icon: Building2, blurb: "The security offered for the loan" },
  conditions: { label: "Conditions", icon: ShieldQuestion, blurb: "Purpose, structure and economic context" },
};

function scoreBarColor(score: number): string {
  if (score >= 80) return "[&>div]:bg-emerald-600";
  if (score >= 60) return "[&>div]:bg-amber-500";
  return "[&>div]:bg-red-600";
}

function formatMetricName(name: string): string {
  return name.replace(/_/g, " ");
}

function formatRawValue(value: unknown, unit: string | null): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    const formatted = Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  return String(value).replace(/_/g, " ");
}

function GroupCard({ five_c, group, completeness }: { five_c: FiveC; group: GroupScore | undefined; completeness?: string }) {
  const meta = FIVE_C_META[five_c];
  const Icon = meta.icon;
  const notComputed = !group || group.state !== "computed" || group.score === null;

  return (
    <div className="rounded-xl border border-border bg-background p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
          <div>
            <p className="font-semibold">{meta.label}</p>
            <p className="text-xs text-muted-foreground">{meta.blurb}</p>
          </div>
        </div>
        {!notComputed && <span className="text-xl font-semibold tabular-nums">{group!.score!.toFixed(0)}</span>}
      </div>

      {notComputed ? (
        <div className="flex items-start gap-2 rounded-lg border border-dashed border-input bg-secondary/30 p-2.5 text-xs text-muted-foreground">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>
            {completeness === "not_applicable"
              ? "Not applicable to this product."
              : "Not yet assessed — insufficient data or this part of the engine isn't built out yet."}
          </span>
        </div>
      ) : (
        <>
          <Progress value={group!.score!} className={cn("mb-3", scoreBarColor(group!.score!))} />
          <ul className="space-y-1.5 text-xs">
            {group!.metrics_used.map((m) => (
              <li key={m.metric} className="flex items-center justify-between gap-2">
                <span className="capitalize text-muted-foreground">{formatMetricName(m.metric)}</span>
                <span className="tabular-nums">
                  {formatRawValue(m.raw_value, m.unit)}
                  <span className="ml-1.5 text-muted-foreground">({m.normalized_score.toFixed(0)}/100)</span>
                </span>
              </li>
            ))}
            {group!.metrics_skipped.map((m) => (
              <li key={m.metric} className="flex items-center justify-between gap-2 text-muted-foreground">
                <span className="capitalize">{formatMetricName(m.metric)}</span>
                <span className="italic">{m.reason.replace(/_/g, " ")}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default function ApplicationReportPage({ params }: { params: { bankId: string; applicationId: string } }) {
  const [report, setReport] = useState<ApplicationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    getApplicationReport(params.applicationId)
      .then(setReport)
      .catch((err: Error) => setError(err.message));
  }, [params.applicationId]);

  useEffect(load, [load]);

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-10">
      <Link
        href={`/admin/banks/${params.bankId}/applications`}
        className="mb-6 flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        All applications
      </Link>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {!report && !error && <p className="p-6 text-sm text-muted-foreground">Loading…</p>}

      {report && (
        <>
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                {report.product_name ?? report.product_code}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {report.product_code} &middot; {report.session_id} &middot; status:{" "}
                <span className="capitalize">{report.status.replace(/_/g, " ")}</span>
              </p>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <div className="flex items-center gap-1.5">
                <Badge className={TIER_BADGE[report.tier] ?? ""}>{TIER_LABEL[report.tier] ?? report.tier}</Badge>
                <Badge className={RISK_BADGE[report.risk_profile.category] ?? ""}>
                  {report.risk_profile.category} risk
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Generated {new Date(report.generated_at).toLocaleString()}
              </p>
            </div>
          </div>

          {report.narrative_summary && (
            <div className="mb-8 flex gap-3 rounded-xl border border-border bg-secondary/20 p-4 shadow-sm">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              <p className="text-sm">{report.narrative_summary}</p>
            </div>
          )}

          {report.risk_profile.factors.length > 0 && (
            <div className="mb-8 rounded-xl border border-border bg-background p-5 shadow-sm">
              <h2 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                Risk factors
              </h2>
              <ul className="space-y-2.5">
                {report.risk_profile.factors.map((factor, index) => (
                  <li key={index} className="flex items-start gap-2.5 text-sm">
                    <span
                      className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", RISK_FACTOR_DOT[factor.severity])}
                      aria-hidden="true"
                    />
                    <div>
                      <span className="font-medium">{factor.label}</span>
                      <span className="text-muted-foreground"> &mdash; {factor.detail}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report.applicant_summary.length > 0 && (
            <div className="mb-8 rounded-xl border border-border bg-background p-5 shadow-sm">
              <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Applicant &amp; loan summary
              </h2>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
                {report.applicant_summary.map((fact) => (
                  <div key={fact.id}>
                    <dt className="text-xs text-muted-foreground">{fact.label}</dt>
                    <dd className="text-sm font-medium capitalize">{formatFactValue(fact.value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          <div className="mb-8 rounded-xl border border-border bg-background p-5 shadow-sm">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">Overall weighted score</p>
              <p className="text-3xl font-semibold tabular-nums">
                {report.overall_score !== null ? report.overall_score.toFixed(0) : "—"}
                <span className="text-base font-normal text-muted-foreground">/100</span>
              </p>
            </div>
            {report.overall_score !== null && (
              <Progress value={report.overall_score} className={cn("h-2.5", scoreBarColor(report.overall_score))} />
            )}
            {Object.keys(report.weights_applied).length > 0 && (
              <p className="mt-3 text-xs text-muted-foreground">
                Weighted by: {FIVE_C_ORDER.filter((c) => report.weights_applied[c] !== undefined)
                  .map((c) => `${FIVE_C_META[c].label} ${report.weights_applied[c]}%`)
                  .join(" · ")}
              </p>
            )}
          </div>

          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FIVE_C_ORDER.map((c) => (
              <GroupCard
                key={c}
                five_c={c}
                group={report.group_scores[c]}
                completeness={report.data_completeness[c]}
              />
            ))}
          </div>

          {report.key_figures.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Key figures
              </h2>
              <div className="overflow-x-auto rounded-xl border border-border bg-background shadow-sm">
                <table className="w-full text-left text-sm">
                  <tbody>
                    {report.key_figures.map((figure, index) => (
                      <tr
                        key={figure.metric}
                        className={cn(
                          "border-b border-border last:border-0",
                          index % 2 === 1 && "bg-secondary/10",
                        )}
                      >
                        <td className="px-4 py-2.5 text-muted-foreground">{figure.label}</td>
                        <td className="px-4 py-2.5 text-right font-medium tabular-nums">
                          {formatFactValue(figure.value)}
                          {figure.unit && <span className="ml-1 text-xs text-muted-foreground">{figure.unit}</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {report.policy_comparison.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Policy comparison
              </h2>
              <div className="overflow-x-auto rounded-xl border border-border bg-background shadow-sm">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="px-4 py-3 font-medium">Metric</th>
                      <th className="px-4 py-3 font-medium">Value</th>
                      <th className="px-4 py-3 font-medium">Threshold</th>
                      <th className="px-4 py-3 font-medium" />
                    </tr>
                  </thead>
                  <tbody>
                    {report.policy_comparison.map((cmp, index) => (
                      <tr
                        key={cmp.metric}
                        className={cn(
                          "border-b border-border last:border-0",
                          index % 2 === 1 && "bg-secondary/10",
                        )}
                      >
                        <td className="px-4 py-2.5">{cmp.label}</td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {formatFactValue(cmp.value)}
                          {cmp.unit && <span className="ml-1 text-xs text-muted-foreground">{cmp.unit}</span>}
                        </td>
                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                          {formatFactValue(cmp.threshold)} {cmp.unit} &mdash; {cmp.threshold_label}
                        </td>
                        <td className="px-4 py-2.5">
                          {cmp.meets_threshold ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" aria-hidden="true" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {report.conditions_of_approval.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Conditions of approval
              </h2>
              <div className="divide-y divide-border rounded-xl border border-border bg-background shadow-sm">
                {report.conditions_of_approval.map((condition) => (
                  <div key={condition.id} className="flex items-start justify-between gap-3 p-4">
                    <div>
                      <p className="text-sm font-medium capitalize">
                        {FIVE_C_META[condition.category as FiveC]?.label ?? condition.category}
                      </p>
                      <p className="text-sm">{condition.text}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{condition.reason}</p>
                    </div>
                    <Badge variant={condition.blocking ? "default" : "outline"} className="shrink-0">
                      {condition.blocking ? "Blocking" : "Advisory"}
                    </Badge>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Rule-based indicator (informational only)
            </h2>
            <div className="rounded-xl border border-border bg-secondary/20 p-4 text-sm shadow-sm">
              <p className="mb-2 text-xs text-muted-foreground">
                The categorical rule engine&apos;s own tier — kept for cross-checking, but the weighted
                score above is the recommended decision.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Badge className={TIER_BADGE[report.rule_based_indicator.tier] ?? ""}>
                  {TIER_LABEL[report.rule_based_indicator.tier] ?? report.rule_based_indicator.tier}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {report.rule_based_indicator.fail_count} fail · {report.rule_based_indicator.flag_count} flag ·{" "}
                  {report.rule_based_indicator.provisional_count} provisional
                </span>
              </div>
            </div>
          </section>

          {(report.documents.length > 0 || report.verifications.length > 0) && (
            <section className="mt-8">
              <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Documents &amp; verification
              </h2>
              <div className="rounded-xl border border-border bg-background shadow-sm">
                {report.documents.length > 0 && (
                  <div className="divide-y divide-border">
                    {report.documents.map((doc) => (
                      <div key={doc.document_id} className="flex items-center justify-between gap-3 p-4">
                        <div className="flex items-center gap-2.5">
                          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <div>
                            <p className="text-sm font-medium">{doc.original_filename}</p>
                            <p className="text-xs capitalize text-muted-foreground">
                              {doc.verification_type.replace(/_/g, " ")} &middot; uploaded {formatDateTime(doc.uploaded_at)}
                            </p>
                          </div>
                        </div>
                        <Badge variant={doc.status === "extracted" ? "secondary" : "outline"} className="capitalize">
                          {doc.status.replace(/_/g, " ")}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
                {report.verifications.length > 0 && (
                  <div className={cn("p-4", report.documents.length > 0 && "border-t border-border")}>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Declared vs. verified
                    </p>
                    <ul className="space-y-1.5 text-sm">
                      {report.verifications.map((v, index) => (
                        <li key={`${v.slot_id}-${index}`} className="flex items-center justify-between gap-3">
                          <span className="capitalize text-muted-foreground">{v.slot_id.replace(/_/g, " ")}</span>
                          <span className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              declared &ldquo;{v.declared_value}&rdquo; &middot; found &ldquo;{v.extracted_value}&rdquo;
                            </span>
                            <Badge variant={v.status === "match" ? "secondary" : "outline"} className="capitalize">
                              {v.status.replace(/_/g, " ")}
                            </Badge>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {report.transcript.length > 0 && (
            <details className="mt-8 rounded-xl border border-border bg-background shadow-sm">
              <summary className="flex cursor-pointer list-none items-center gap-2 p-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
                Conversation transcript ({report.transcript.length} messages)
              </summary>
              <div className="max-h-96 space-y-3 overflow-y-auto border-t border-border p-4">
                {report.transcript.map((message, index) => (
                  <div key={index} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                    <div
                      className={cn(
                        "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                        message.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary/50",
                      )}
                    >
                      {message.content}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}
