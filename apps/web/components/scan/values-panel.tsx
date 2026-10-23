"use client";

import { Crosshair } from "lucide-react";
import Link from "next/link";

import type { ScanPhase } from "@/components/scan/scan-stage";
import { fieldLabel, formatField, money } from "@/lib/documents/labels";
import type { ExtractResponse } from "@/lib/types/documents";
import { cn } from "@/lib/utils";

type Props = {
  result: ExtractResponse | null;
  phase: ScanPhase;
  revealed: ReadonlySet<string>;
  hasBoxes: boolean;
  sampleId: string | null;
  onActive: (id: string | null) => void;
};

const SKELETON_ROWS = 5;

function Row({ shown, children }: { shown: boolean; children: React.ReactNode }) {
  return (
    <li className={cn("transition-all duration-300", shown ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0")}>
      {children}
    </li>
  );
}

export function ValuesPanel({ result, phase, revealed, hasBoxes, sampleId, onActive }: Props) {
  const fields = result?.fields ?? [];
  const transactions = result?.transactions ?? [];
  const rowsRead = transactions.filter((_, index) => revealed.has(`row:${index}`)).length;
  const fieldsRead = fields.filter((f) => revealed.has(f.id)).length;
  const totalItems = fields.length + (transactions.length > 0 ? 1 : 0);
  const allRowsRead = transactions.length > 0 && rowsRead === transactions.length;
  const credits = transactions.filter((t) => t.direction === "credit").reduce((sum, t) => sum + t.amount, 0);
  const debits = transactions.filter((t) => t.direction === "debit").reduce((sum, t) => sum + t.amount, 0);

  return (
    <div className="rounded-xl border border-border">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Extracted values</h2>
        {result && (
          <span className="text-xs text-muted-foreground">
            {fieldsRead + (allRowsRead ? 1 : 0)} of {totalItems} read
          </span>
        )}
      </header>

      {!result ? (
        <div className="p-4">
          {phase === "idle" ? (
            <p className="text-sm text-muted-foreground">Press Scan to read this document. Each value appears here as it is found.</p>
          ) : (
            <ul className="space-y-3" aria-label="Reading the document">
              {Array.from({ length: SKELETON_ROWS }, (_, index) => (
                <li key={index} className="space-y-1.5">
                  <div className="h-2.5 w-24 animate-pulse rounded bg-secondary" />
                  <div className="h-4 w-48 animate-pulse rounded bg-secondary" />
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : !result.matches_claimed_type ? (
        <div className="space-y-1 p-4">
          <p className="text-sm font-medium text-destructive">This does not look like the expected document.</p>
          {result.notes && <p className="text-sm text-muted-foreground">{result.notes}</p>}
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {fields.map((field) => {
            const text = formatField(field);
            const shown = revealed.has(field.id);
            return (
              <Row key={field.id} shown={shown}>
                <div
                  className="flex items-start justify-between gap-3 px-4 py-3"
                  onMouseEnter={() => onActive(field.id)}
                  onMouseLeave={() => onActive(null)}
                >
                  <div className="min-w-0">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      {fieldLabel(field.id)}
                    </p>
                    <p className={cn("text-sm font-medium", !text && "font-normal italic text-muted-foreground")}>
                      {text || "Not visible on the document"}
                    </p>
                  </div>
                  {hasBoxes && text && (
                    <Crosshair className="mt-1 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-label="Located on the page" />
                  )}
                </div>
              </Row>
            );
          })}

          {transactions.length > 0 && (
            <Row shown={rowsRead > 0 || revealed.has("transactions")}>
              <div className="px-4 py-3">
                <div className="flex items-baseline justify-between">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Transactions</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {rowsRead} <span className="font-normal text-muted-foreground">of {transactions.length} found</span>
                  </p>
                </div>
                {allRowsRead && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Money in {money(credits)} · Money out {money(debits)}
                  </p>
                )}
                <details className="group mt-2">
                  <summary className="cursor-pointer list-none text-xs font-medium text-primary underline-offset-4 hover:underline">
                    Show the lines
                  </summary>
                  <ul className="mt-2 max-h-56 overflow-y-auto rounded-md border border-border">
                    {transactions.map((t, index) => (
                      <li
                        key={index}
                        onMouseEnter={() => onActive(`row:${index}`)}
                        onMouseLeave={() => onActive(null)}
                        className={cn(
                          "flex items-center justify-between gap-3 border-b border-border px-3 py-1.5 text-xs last:border-b-0 hover:bg-secondary/60",
                          !revealed.has(`row:${index}`) && "opacity-40",
                        )}
                      >
                        <span className="truncate">{t.description}</span>
                        <span
                          className={cn(
                            "shrink-0 tabular-nums",
                            t.direction === "credit" && "font-medium text-emerald-700 dark:text-emerald-400",
                          )}
                        >
                          {t.direction === "credit" ? "+" : "-"}
                          {money(t.amount)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            </Row>
          )}
        </ul>
      )}

      {result && phase === "done" && (
        <footer className="space-y-1.5 border-t border-border bg-secondary/30 px-4 py-3 text-xs text-muted-foreground">
          <p>
            {result.source === "recorded" && result.recording
              ? `Real AI output, recorded ${new Date(result.recording.recorded_at).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })} with ${result.recording.model}.`
              : result.method === "pdf_text"
                ? `Read directly from the PDF's own text in ${result.duration_ms} ms. No AI model was used.`
                : `Read live by the AI model in ${(result.duration_ms / 1000).toFixed(1)} seconds.`}
          </p>
          {result.checks?.reconciled && (
            <p className="font-medium text-emerald-700 dark:text-emerald-400">
              Balance check passed: all {result.checks.rows} rows add up to the closing balance.
            </p>
          )}
          {sampleId && (
            <p>
              <Link
                href={`/playground/documents?sample=${sampleId}`}
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                See how these values are checked and used in the assessment
              </Link>
            </p>
          )}
        </footer>
      )}
    </div>
  );
}
