"use client";

import { AlertTriangle, CheckCircle2, ChevronRight, CircleHelp, XCircle } from "lucide-react";
import { useState } from "react";

import { GROUP_LABELS, METRIC_LABELS, prettify } from "@/lib/playground/fields";
import {
  GROUP_ORDER,
  type AssessResponse,
  type MetricResult,
  type RouteTier,
  type RuleResult,
} from "@/lib/types/playground";
import { cn } from "@/lib/utils";

const label = (metric: string) => METRIC_LABELS[metric] ?? prettify(metric);

const TIER_META: Record<RouteTier, { title: string; summary: string; box: string; icon: typeof XCircle }> = {
  auto_eligible: {
    title: "Approve recommended",
    summary: "All configured rules passed. A staff member makes the final decision.",
    box: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
    icon: CheckCircle2,
  },
  underwriter_review: {
    title: "Underwriter review",
    summary: "No hard failures, but at least one flag needs a person to look at it.",
    box: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
    icon: AlertTriangle,
  },
  conditional: {
    title: "Conditional",
    summary: "Some checks could not run because information is missing. Nothing has failed yet.",
    box: "border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-100",
    icon: CircleHelp,
  },
  decline_recommended: {
    title: "Decline recommended",
    summary: "At least one hard rule failed.",
    box: "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100",
    icon: XCircle,
  },
};

const CHANNEL_LABELS: Record<string, string> = {
  declaration: "Declared by applicant",
  document: "From a document",
  bureau: "Credit bureau",
  open_banking: "Bank statement",
  registry: "Registry",
  valuation: "Valuation",
  benchmark: "Benchmark",
  policy: "Bank policy",
  derived: "Calculated",
};

function formatNumber(value: number, unit: string | null): string {
  if (!unit) return String(value);
  if (unit.startsWith("AUD")) {
    const big = Math.abs(value) >= 1000;
    const amount = new Intl.NumberFormat("en-AU", {
      style: "currency",
      currency: "AUD",
      minimumFractionDigits: big || Number.isInteger(value) ? 0 : 2,
      maximumFractionDigits: big ? 0 : 2,
    }).format(value);
    const per = unit.split("/")[1];
    if (!per) return amount;
    return `${amount} / ${per === "statement_period" ? "statement" : per}`;
  }
  if (unit.startsWith("%")) {
    const rest = unit.slice(1).trim();
    return `${value.toFixed(2)}%${rest ? ` ${rest}` : ""}`;
  }
  if (unit === "ratio") return value.toFixed(Math.abs(value) < 1 ? 3 : 2);
  if (unit === "months") return `${value} months`;
  if (unit === "years") return `${value} years`;
  return String(value);
}

function formatMetric(metric: MetricResult): string {
  if (metric.state === "not_applicable") return "Not applicable";
  if (metric.state !== "computed" || metric.value === null) return "Unavailable";
  const { value, unit } = metric;
  if (typeof value === "number") return formatNumber(value, unit);
  if (typeof value === "string") return prettify(value);
  return Object.entries(value)
    .map(([key, item]) => `${prettify(key)}: ${String(item)}`)
    .join(" · ");
}

function formatInput(value: unknown): string {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (value === null || value === undefined) return "-";
  return String(value);
}

function KeyFigure({ name, response }: { name: string; response: AssessResponse }) {
  const metric = Object.values(response.groups)
    .map((group) => group[name])
    .find(Boolean);
  const usable = metric?.state === "computed" && metric.value !== null;
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-[11px] font-medium text-muted-foreground">{label(name)}</p>
      <p className={cn("mt-1 text-lg font-semibold tabular-nums", !usable && "text-muted-foreground")}>
        {metric && usable ? formatMetric(metric) : "-"}
      </p>
    </div>
  );
}

function RuleCard({ rule }: { rule: RuleResult }) {
  const fail = rule.status === "fail";
  return (
    <li
      className={cn(
        "rounded-md border border-border border-l-4 p-3",
        fail ? "border-l-destructive" : "border-l-amber-500",
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase",
            fail
              ? "bg-destructive/10 text-destructive"
              : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
          )}
        >
          {rule.status}
        </span>
        <span className="text-sm font-medium">{prettify(rule.rule_id)}</span>
      </div>
      {rule.message && <p className="mt-1 text-sm text-muted-foreground">{rule.message}</p>}
      {rule.inputs && Object.keys(rule.inputs).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(rule.inputs).map(([metric, value]) => (
            <span key={metric} className="rounded bg-secondary px-2 py-0.5 font-mono text-[11px]">
              {label(metric)} = {formatInput(value)}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function MetricRow({ name, metric }: { name: string; metric: MetricResult }) {
  const [open, setOpen] = useState(false);
  const muted = metric.state !== "computed";
  const reason = metric.inputs?.reason;
  const details = metric.inputs ? Object.entries(metric.inputs).filter(([key]) => key !== "reason") : [];
  const expandable = details.length > 0 || Boolean(reason) || metric.state === "computed";

  return (
    <li className="border-t border-border first:border-t-0">
      <button
        type="button"
        disabled={!expandable}
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-secondary/50 disabled:cursor-default disabled:hover:bg-transparent"
        aria-expanded={open}
      >
        <ChevronRight
          className={cn("h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform", open && "rotate-90")}
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1 truncate text-sm">{label(name)}</span>
        <span
          className={cn(
            "shrink-0 text-sm font-medium tabular-nums",
            muted && "font-normal italic text-muted-foreground",
          )}
        >
          {formatMetric(metric)}
        </span>
      </button>
      {open && (
        <div className="bg-secondary/30 px-9 py-2.5 text-xs">
          <p className="text-muted-foreground">
            Source: <span className="font-medium text-foreground">{CHANNEL_LABELS[metric.channel] ?? metric.channel}</span>
          </p>
          {typeof reason === "string" && (
            <p className="mt-1 text-muted-foreground">Why not computed: {prettify(reason)}</p>
          )}
          {details.length > 0 && (
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
              {details.map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="text-muted-foreground">{prettify(key)}</dt>
                  <dd className="font-mono tabular-nums">{formatInput(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </li>
  );
}

function ApprovalConditions({ response }: { response: AssessResponse }) {
  const conditions = response.conditions_of_approval ?? [];
  const declined = response.route.tier === "decline_recommended";
  if (conditions.length === 0 && !declined) return null;

  return (
    <section>
      <h3 className="mb-1 text-sm font-semibold">Conditions of approval</h3>
      {declined ? (
        <p className="rounded-md border border-border bg-secondary/30 p-3 text-sm text-muted-foreground">
          A decline is recommended, so there are no conditions to satisfy.
        </p>
      ) : (
        <>
          <p className="mb-2 text-xs text-muted-foreground">
            What has to be in place before this loan can settle, and why each item is needed.
          </p>
          <ul className="space-y-2">
            {conditions.map((condition) => (
              <li key={condition.id} className="rounded-md border border-border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold uppercase">
                    {GROUP_LABELS[condition.category]?.title ?? condition.category}
                  </span>
                  <span
                    className={cn(
                      "text-[11px] font-medium",
                      condition.blocking ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {condition.blocking ? "Before settlement" : "Recommended"}
                  </span>
                </div>
                <p className="mt-1.5 text-sm font-medium">{condition.text}</p>
                <p className="text-xs text-muted-foreground">Why: {condition.reason}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export function ResultsPanel({ response }: { response: AssessResponse }) {
  const tier = TIER_META[response.route.tier];
  const Icon = tier.icon;
  const triggered = response.rule_results.filter((r) => r.status === "fail" || r.status === "flag");
  const provisional = response.rule_results.filter((r) => r.status === "provisional");
  const errors = response.rule_results.filter((r) => r.status === "error");

  return (
    <div className="space-y-6 p-6">
      <section className={cn("flex items-start gap-4 rounded-xl border p-5", tier.box)}>
        <Icon className="mt-0.5 h-8 w-8 shrink-0" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider opacity-70">Assessment outcome</p>
          <h2 className="text-2xl font-semibold">{tier.title}</h2>
          <p className="mt-1 text-sm opacity-90">{tier.summary}</p>
          <p className="mt-3 text-xs opacity-80">
            {response.route.fail_count} failed · {response.route.flag_count} flagged ·{" "}
            {response.route.provisional_count} waiting on data · {response.metrics_computed} of{" "}
            {response.metrics_total} measures calculated
          </p>
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold">Key figures</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {["proposed_repayment", "monthly_surplus", "nsr", "dti", "contribution_pct", "credit_score"].map((name) => (
            <KeyFigure key={name} name={name} response={response} />
          ))}
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold">Why this outcome</h3>
        {triggered.length === 0 && errors.length === 0 ? (
          <p className="rounded-md border border-border bg-secondary/30 p-3 text-sm text-muted-foreground">
            No rule failed or flagged.
            {provisional.length > 0 && " Some rules could not run yet, see below."}
          </p>
        ) : (
          <ul className="space-y-2">
            {triggered.map((rule) => (
              <RuleCard key={rule.rule_id} rule={rule} />
            ))}
            {errors.map((rule) => (
              <li key={rule.rule_id} className="rounded-md border border-destructive p-3 text-sm">
                Rule {prettify(rule.rule_id)} could not be evaluated: {rule.detail}
              </li>
            ))}
          </ul>
        )}

        {provisional.length > 0 && (
          <details className="group mt-3 rounded-md border border-border">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm">
              <ChevronRight
                className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90"
                aria-hidden="true"
              />
              {provisional.length} {provisional.length === 1 ? "rule is" : "rules are"} waiting on data
            </summary>
            <ul className="space-y-1 border-t border-border px-3 py-2 text-xs text-muted-foreground">
              {provisional.map((rule) => (
                <li key={rule.rule_id}>
                  <span className="font-medium text-foreground">{prettify(rule.rule_id)}</span> needs{" "}
                  {rule.missing?.map(label).join(", ")}
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <ApprovalConditions response={response} />

      <section className="rounded-md border border-border p-3 text-sm">
        <span className="font-medium">Credit bureau: </span>
        {response.bureau.status === "pulled" ? (
          <span className="text-muted-foreground">
            report pulled ({prettify(response.bureau.scenario)} file, {response.bureau.report_id})
          </span>
        ) : (
          <span className="text-muted-foreground">not contacted. {response.bureau.reason}.</span>
        )}
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold">Every measure, by the five Cs</h3>
        <p className="mb-3 text-xs text-muted-foreground">Click any measure to see the numbers behind it.</p>
        <div className="grid gap-4 xl:grid-cols-2">
          {GROUP_ORDER.map((group) => {
            const metrics = Object.entries(response.groups[group]);
            const done = metrics.filter(([, m]) => m.state === "computed").length;
            return (
              <div key={group} className="rounded-lg border border-border">
                <div className="flex items-baseline justify-between border-b border-border bg-secondary/40 px-3 py-2">
                  <div>
                    <h4 className="text-sm font-semibold">{GROUP_LABELS[group].title}</h4>
                    <p className="text-[11px] text-muted-foreground">{GROUP_LABELS[group].blurb}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {done}/{metrics.length}
                  </span>
                </div>
                <ul>
                  {metrics.map(([name, metric]) => (
                    <MetricRow key={name} name={name} metric={metric} />
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </section>

      <p className="border-t border-border pt-4 text-xs text-muted-foreground">
        Every figure and rule above is calculated by code from the inputs on the left. No AI model is involved in
        the decision.
      </p>
    </div>
  );
}
