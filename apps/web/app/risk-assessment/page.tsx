"use client";

import { useState } from "react";
import { AlertTriangle, FileSearch, Landmark, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { RiskReportView } from "@/components/risk-report";
import { assessRisk } from "@/lib/api";
import type { RiskAssessmentReport } from "@/lib/types/risk-assessment";

const SAMPLE_APPLICATION = {
  applicant: {
    name: "Daniel Osei",
    dob: "1990-07-22",
    address: "45 Banksia Avenue, Marrickville NSW 2204",
    employment: {
      status: "Full-time",
      employer: "Acme Pty Ltd",
      years_in_role: 3,
      income: 95000,
      income_frequency: "Annually",
    },
    monthly_expenses: 2100,
  },
  loan: { amount: 40000, purpose: "Car purchase", term_months: 60, product_type: "car" },
  existing_debt: {
    loans: [{ type: "personal loan", balance: 5000, monthly_repayment: 150 }],
    credit_cards: [{ limit: 5000, balance: 1200 }],
  },
  collateral: { asset_type: "Vehicle", estimated_value: 42000, deposit_amount: 5000 },
};

type PageState = "idle" | "loading" | "error" | "ready";

export default function RiskAssessmentPage() {
  const [draft, setDraft] = useState(JSON.stringify(SAMPLE_APPLICATION, null, 2));
  const [pageState, setPageState] = useState<PageState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [report, setReport] = useState<RiskAssessmentReport | null>(null);

  async function handleAssess() {
    let application: Record<string, unknown>;
    try {
      application = JSON.parse(draft);
    } catch {
      setPageState("error");
      setErrorMessage("That's not valid JSON — check for a missing comma or bracket.");
      return;
    }

    setPageState("loading");
    setErrorMessage(null);

    try {
      const result = await assessRisk(application);
      setReport(result);
      setPageState("ready");
    } catch {
      setPageState("error");
      setErrorMessage("Couldn't reach the assessment service. Please try again.");
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl p-4 sm:p-6">
      <header className="mb-6 flex items-center gap-2">
        <Landmark className="h-5 w-5 text-primary" aria-hidden="true" />
        <h1 className="text-lg font-semibold">5 C&apos;s Credit Risk Assessment</h1>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <section className="flex flex-col gap-3">
          <label htmlFor="application-json" className="text-sm font-medium">
            Application JSON
          </label>
          <textarea
            id="application-json"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            spellCheck={false}
            className="min-h-[420px] w-full rounded-md border border-input bg-background p-3 font-mono text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void handleAssess()} disabled={pageState === "loading"}>
              {pageState === "loading" && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              Assess application
            </Button>
            <Button
              variant="outline"
              type="button"
              onClick={() => setDraft(JSON.stringify(SAMPLE_APPLICATION, null, 2))}
            >
              Load sample
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Fields can be partial or missing — the assessment degrades gracefully and always returns
            a report, flagging what&apos;s absent.
          </p>
        </section>

        <section className="flex flex-col gap-4">
          {pageState === "idle" && (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border p-10 text-center text-muted-foreground">
              <FileSearch className="h-6 w-6" aria-hidden="true" />
              <p className="text-sm">Submit an application to see its risk assessment report.</p>
            </div>
          )}

          {pageState === "loading" && (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
              <p className="text-sm">Assessing application...</p>
            </div>
          )}

          {pageState === "error" && (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center">
              <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
              <p className="text-sm font-medium">{errorMessage}</p>
            </div>
          )}

          {pageState === "ready" && report && <RiskReportView report={report} />}
        </section>
      </div>
    </div>
  );
}
