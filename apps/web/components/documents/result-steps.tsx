"use client";

import { CheckCircle2, CircleHelp, XCircle } from "lucide-react";
import type { ReactNode } from "react";

import { categoryLabel, describeCheck, fieldLabel, formatField, money } from "@/lib/documents/labels";
import type { DocumentTypeInfo, ExtractResponse, Verification } from "@/lib/types/documents";
import { cn } from "@/lib/utils";

type Tone = "ok" | "bad" | "neutral";

function Step({ n, title, tone, children }: { n: number; title: string; tone: Tone; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-border">
      <header className="flex items-center gap-3 border-b border-border px-4 py-3">
        <span
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
            tone === "ok" && "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
            tone === "bad" && "bg-destructive/10 text-destructive",
            tone === "neutral" && "bg-secondary text-secondary-foreground",
          )}
        >
          {n}
        </span>
        <h3 className="text-sm font-semibold">{title}</h3>
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

const STATUS_META = {
  match: { label: "Match", icon: CheckCircle2, cls: "text-emerald-700 dark:text-emerald-400" },
  mismatch: { label: "Mismatch", icon: XCircle, cls: "text-destructive" },
  missing: { label: "Not compared", icon: CircleHelp, cls: "text-muted-foreground" },
  on_file: { label: "Kept on file", icon: CircleHelp, cls: "text-muted-foreground" },
} as const;

function VerificationRow({ v, label }: { v: Verification; label: string }) {
  const meta = STATUS_META[v.status];
  const Icon = meta.icon;
  const note =
    v.status === "missing"
      ? v.declared_value === ""
        ? "The applicant has not given an answer to compare against."
        : "The AI could not find this on the document."
      : describeCheck(v.compare, v.tolerance_pct);
  return (
    <tr className="border-t border-border align-top first:border-t-0">
      <td className="py-2.5 pr-3">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-[11px] text-muted-foreground">{note}</p>
      </td>
      <td className="py-2.5 pr-3 text-sm">{v.declared_value || <span className="text-muted-foreground">-</span>}</td>
      <td className="py-2.5 pr-3 text-sm">{v.extracted_value || <span className="text-muted-foreground">-</span>}</td>
      <td className="py-2.5">
        <span className={cn("flex items-center gap-1.5 text-sm font-medium", meta.cls)}>
          <Icon className="h-4 w-4" aria-hidden="true" />
          {meta.label}
        </span>
      </td>
    </tr>
  );
}

function CategoryChip({ category }: { category: string | null }) {
  const tone =
    category === "income"
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
      : category === null || category === "other" || category === "transfer"
        ? "bg-secondary text-muted-foreground"
        : "bg-primary/10 text-foreground";
  return <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", tone)}>{categoryLabel(category)}</span>;
}

export function ResultSteps({ response, docType }: { response: ExtractResponse; docType: DocumentTypeInfo | undefined }) {
  const typeName = docType?.name ?? "document";
  const impact = response.assessment_impact;
  const expenseBreakdown = Object.entries(impact?.verified_expenses.inputs ?? {}).sort((a, b) => b[1] - a[1]);
  const maxExpense = expenseBreakdown[0]?.[1] ?? 1;
  const savingsInputs = impact?.genuine_savings.inputs;
  const checkLabels = new Map(docType?.checks.map((c) => [c.slot_id, c.label]));

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        {response.source === "recorded" && response.recording
          ? `Replayed from a real AI run saved on ${new Date(response.recording.recorded_at).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })} using ${response.recording.model}. The comparison below runs live.`
          : response.method === "pdf_text"
            ? `Read directly from the PDF's own text in ${response.duration_ms} ms. No AI model was needed to read it.`
            : `Live AI extraction, completed in ${(response.duration_ms / 1000).toFixed(1)} seconds.`}
      </p>
      {response.warnings.map((warning) => (
        <p
          key={warning}
          className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
        >
          {warning}
        </p>
      ))}

      <Step n={1} title="Is it the right kind of document?" tone={response.matches_claimed_type ? "ok" : "bad"}>
        {response.matches_claimed_type ? (
          <p className="text-sm">
            Yes, this looks like a <span className="font-medium">{typeName.toLowerCase()}</span>.
            {response.notes && <span className="text-muted-foreground"> {response.notes}.</span>}
          </p>
        ) : (
          <div className="space-y-1">
            <p className="text-sm font-medium text-destructive">This does not look like a {typeName.toLowerCase()}.</p>
            {response.notes && <p className="text-sm text-muted-foreground">{response.notes}</p>}
            <p className="text-xs text-muted-foreground">
              Nothing is extracted from the wrong document, and the applicant would be asked to upload the right one.
            </p>
          </div>
        )}
      </Step>

      {response.matches_claimed_type && (
        <>
          <Step n={2} title={response.method === "pdf_text" ? "What was read from the PDF" : "What the AI read"} tone="neutral">
            <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
              {response.fields.map((field) => {
                const text = formatField(field);
                return (
                  <div key={field.id}>
                    <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      {fieldLabel(field.id)}
                    </dt>
                    <dd className={cn("text-sm font-medium", !text && "font-normal italic text-muted-foreground")}>
                      {text || "Not visible on the document"}
                    </dd>
                  </div>
                );
              })}
            </dl>
            {response.checks?.reconciled && (
              <p className="mt-3 flex items-start gap-2 rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>
                  Balance check passed: {money(response.checks.opening_balance)} opening + {money(response.checks.total_in)} in
                  − {money(response.checks.total_out)} out = {money(response.checks.closing_balance)}, the closing balance on
                  the statement. Each of the {response.checks.rows} rows follows from the balance before it, so nothing was
                  missed or misread.
                </span>
              </p>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              {response.method === "pdf_text"
                ? "Values are taken exactly as printed in the PDF. If a value cannot be found or does not add up, the document is passed to the AI instead."
                : "The AI only reads what is printed on the page. If a value is not visible it says so, and never guesses."}
            </p>
          </Step>

          <Step
            n={3}
            title="Does it match what the applicant told us?"
            tone={
              response.verifications.some((v) => v.status === "mismatch")
                ? "bad"
                : response.verifications.some((v) => v.status === "match")
                  ? "ok"
                  : "neutral"
            }
          >
            {response.verifications.length === 0 || response.verifications.every((v) => v.slot_id === "") ? (
              <p className="text-sm text-muted-foreground">
                There is no comparison rule for this document type, so the fields are stored as evidence only.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-left">
                  <thead>
                    <tr className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      <th className="pb-2 pr-3 font-medium">Check</th>
                      <th className="pb-2 pr-3 font-medium">Applicant said</th>
                      <th className="pb-2 pr-3 font-medium">Document shows</th>
                      <th className="pb-2 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {response.verifications.map((v) => (
                      <VerificationRow key={v.slot_id} v={v} label={checkLabels.get(v.slot_id) ?? v.slot_id} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              This comparison is ordinary code with fixed tolerances, not AI judgement.
            </p>
          </Step>
        </>
      )}

      {response.transactions && response.transactions.length > 0 && (
        <>
          <Step n={4} title="Transactions sorted into spending categories" tone="neutral">
            <div className="max-h-80 overflow-y-auto rounded-md border border-border">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-secondary text-[11px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Date</th>
                    <th className="px-3 py-2 font-medium">Description</th>
                    <th className="px-3 py-2 text-right font-medium">Amount</th>
                    <th className="px-3 py-2 font-medium">Category</th>
                  </tr>
                </thead>
                <tbody>
                  {response.transactions.map((t, index) => (
                    <tr key={index} className="border-t border-border text-sm">
                      <td className="whitespace-nowrap px-3 py-1.5 text-muted-foreground">{t.date}</td>
                      <td className="px-3 py-1.5">{t.description}</td>
                      <td
                        className={cn(
                          "whitespace-nowrap px-3 py-1.5 text-right tabular-nums",
                          t.direction === "credit" && "font-medium text-emerald-700 dark:text-emerald-400",
                        )}
                      >
                        {t.direction === "credit" ? "+" : "-"}
                        {money(t.amount)}
                      </td>
                      <td className="px-3 py-1.5">
                        <CategoryChip category={t.category} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              A second AI step assigns each line to one fixed list of categories. It cannot invent a category, and anything
              unclear becomes Other.
            </p>
          </Step>

          {impact && (
            <Step n={5} title="What this means for the assessment" tone="neutral">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-border p-4">
                  <p className="text-xs font-medium text-muted-foreground">Living expenses seen on the statement</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">
                    {impact.verified_expenses.value !== null ? money(impact.verified_expenses.value) : "Unavailable"}
                  </p>
                  {impact.statement_days && (
                    <p className="text-[11px] text-muted-foreground">Over {impact.statement_days} days</p>
                  )}
                  <ul className="mt-3 space-y-1.5">
                    {expenseBreakdown.map(([category, amount]) => (
                      <li key={category} className="text-xs">
                        <div className="flex justify-between">
                          <span>{categoryLabel(category)}</span>
                          <span className="tabular-nums text-muted-foreground">{money(amount)}</span>
                        </div>
                        <div className="mt-0.5 h-1.5 rounded-full bg-secondary">
                          <div
                            className="h-1.5 rounded-full bg-primary"
                            style={{ width: `${Math.max(3, (amount / maxExpense) * 100)}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-[11px] text-muted-foreground">
                    The assessment compares this with what the applicant declared and an industry benchmark, and uses the
                    highest.
                  </p>
                </div>

                <div className="rounded-lg border border-border p-4">
                  <p className="text-xs font-medium text-muted-foreground">Genuine savings evidence</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">
                    {impact.genuine_savings.value !== null ? money(impact.genuine_savings.value) : "Unavailable"}
                  </p>
                  {savingsInputs && (
                    <dl className="mt-3 space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <dt>Money in (excluding transfers)</dt>
                        <dd className="tabular-nums text-muted-foreground">{money(savingsInputs.total_credits)}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt>
                          Left out as {savingsInputs.excluded_count === 1 ? "a lump sum" : `${savingsInputs.excluded_count} lump sums`}
                        </dt>
                        <dd className="tabular-nums text-muted-foreground">-{money(savingsInputs.excluded_as_lump_sum)}</dd>
                      </div>
                    </dl>
                  )}
                  <p className="mt-3 text-[11px] text-muted-foreground">
                    One-off deposits such as a gift are not counted as evidence of regular saving, so a large gift cannot make
                    the applicant look like a saver.
                  </p>
                </div>
              </div>
            </Step>
          )}
        </>
      )}
    </div>
  );
}
