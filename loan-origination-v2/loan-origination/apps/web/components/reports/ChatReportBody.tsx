// Shared with both the "View chat report" modal (staff/applications/page.tsx)
// and the standalone printable report page (staff/applications/[id]/report) —
// one rendering of a chat-originated application's full report, so the two
// surfaces can never drift out of sync with each other.
import { type ChatReport } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";

export function statusLabel(status: string) {
  return status
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

function fmtDateTime(iso: string) {
  return new Date(iso).toLocaleString();
}

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

// Matches app.agents.assessment.metric.MetricState in agent-backend —
// "pass"/"fail"/"warn" are rule outcomes (RULE_TONE below), not metric states.
const METRIC_TONE: Record<string, "slate" | "emerald" | "amber" | "red"> = {
  computed: "emerald",
  unavailable: "slate",
  not_applicable: "slate",
  stale: "amber",
};

// Matches app.agents.assessment.rules.engine.evaluate's status vocabulary.
const RULE_TONE: Record<string, "slate" | "emerald" | "amber" | "red"> = {
  fail: "red",
  flag: "amber",
  provisional: "slate",
  error: "red",
  pass: "emerald",
};

const ROUTE_TIER_LABEL: Record<string, string> = {
  auto_eligible: "Auto-eligible",
  underwriter_review: "Underwriter review",
  conditional: "Conditional — missing data",
  decline_recommended: "Decline recommended",
};

function creditScoreTone(score: number): "emerald" | "amber" | "red" {
  if (score >= 700) return "emerald";
  if (score >= 580) return "amber";
  return "red";
}

export function ChatReportBody({ report }: { report: ChatReport }) {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Overview</h3>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-slate-400">Product</dt>
          <dd className="text-slate-800">{report.product_code ?? "—"}</dd>
          <dt className="text-slate-400">Chat status</dt>
          <dd className="text-slate-800">{statusLabel(report.status)}</dd>
          <dt className="text-slate-400">Started</dt>
          <dd className="text-slate-800">{fmtDateTime(report.created_at)}</dd>
          <dt className="text-slate-400">Last activity</dt>
          <dd className="text-slate-800">{fmtDateTime(report.updated_at)}</dd>
        </dl>
      </section>

      {report.slots.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Interview answers</h3>
          <dl className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-100">
            {report.slots.map((s) => (
              <div key={s.slot_key} className="flex items-start justify-between gap-4 px-3 py-2 text-sm">
                <dt className="text-slate-500">{s.slot_key.replace(/_/g, " ")}</dt>
                <dd className="text-right font-medium text-slate-800">{fmtValue(s.value)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Five C&apos;s assessment</h3>
        {report.assessment ? (
          <div className="mt-2">
            <p className="text-xs text-slate-400">
              {report.assessment.metrics_computed} of {report.assessment.metrics_total} metrics computed · run{" "}
              {fmtDateTime(report.assessment.created_at)}
            </p>

            {(() => {
              const creditScore = report.assessment.metrics.credit_score;
              if (!creditScore || creditScore.value === null || creditScore.value === undefined) return null;
              const score = Number(creditScore.value);
              return (
                <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50/60 px-3.5 py-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Credit score</p>
                    <p className="text-[11px] text-slate-400">{creditScore.unit}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-semibold text-slate-900">{score}</span>
                    <Badge tone={creditScoreTone(score)}>{score >= 700 ? "Good" : score >= 580 ? "Fair" : "Poor"}</Badge>
                  </div>
                </div>
              );
            })()}

            <dl className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
              {Object.entries(report.assessment.metrics)
                .filter(([key]) => key !== "credit_score")
                .map(([key, m]) => (
                  <div key={key} className="flex items-center justify-between gap-4 px-3 py-2 text-sm">
                    <dt className="text-slate-500">{key.replace(/_/g, " ")}</dt>
                    <dd className="flex items-center gap-2 text-slate-800">
                      <span>
                        {fmtValue(m.value)}
                        {m.unit ? ` ${m.unit}` : ""}
                      </span>
                      <Badge tone={METRIC_TONE[m.state] ?? "slate"}>{m.state.replace(/_/g, " ")}</Badge>
                    </dd>
                  </div>
                ))}
            </dl>
            {report.assessment.rule_results.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-slate-400">Rules</p>
                <ul className="mt-1 space-y-1">
                  {report.assessment.rule_results.map((r, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <Badge tone={RULE_TONE[r.status] ?? "slate"}>{r.status}</Badge>
                      <span className="text-slate-600">{r.rule_id}</span>
                      {r.message && <span className="text-slate-400">— {r.message}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {report.assessment.route?.tier && (
              <p className="mt-3 text-sm text-slate-600">
                Recommended route:{" "}
                <span className="font-medium text-slate-900">
                  {ROUTE_TIER_LABEL[report.assessment.route.tier] ?? report.assessment.route.tier}
                </span>
              </p>
            )}
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-400">No assessment has been run for this session.</p>
        )}
      </section>

      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Documents</h3>
        {report.documents.length > 0 ? (
          <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-100">
            {report.documents.map((d) => (
              <li key={d.document_id} className="px-3 py-2.5 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-800">{d.verification_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-slate-400">
                      {d.original_filename} · uploaded {fmtDateTime(d.uploaded_at)}
                    </p>
                  </div>
                  <Badge
                    tone={
                      d.status === "extracted" ? "emerald" : d.status === "needs_reupload" ? "red" : "slate"
                    }
                  >
                    {d.status.replace(/_/g, " ")}
                  </Badge>
                </div>
                {d.verifications.length > 0 && (
                  <ul className="mt-1.5 space-y-0.5 pl-0.5">
                    {d.verifications.map((v, i) => (
                      <li key={i} className="flex items-center gap-2 text-xs">
                        <Badge tone={v.status === "match" ? "emerald" : v.status === "mismatch" ? "amber" : "slate"}>
                          {v.status}
                        </Badge>
                        <span className="text-slate-400">
                          {v.slot_id.replace(/_/g, " ")}: told us &ldquo;{v.declared_value}&rdquo;, document says
                          &ldquo;{v.extracted_value}&rdquo;
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-400">No documents uploaded.</p>
        )}
      </section>

      {report.decision && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Decision</h3>
          <div className="mt-2 rounded-lg border border-slate-100 px-3 py-2.5 text-sm">
            <div className="flex items-center gap-2">
              <Badge tone={report.decision.outcome === "approved" ? "emerald" : "amber"}>
                {report.decision.outcome.replace(/_/g, " ")}
              </Badge>
              <span className="text-xs text-slate-400">{fmtDateTime(report.decision.decided_at)}</span>
            </div>
            {report.decision.reasoning && <p className="mt-1.5 text-slate-600">{report.decision.reasoning}</p>}
          </div>
        </section>
      )}

      {report.transcript.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Chat transcript</h3>
          <div className="mt-2 max-h-64 space-y-2 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/60 p-3 print:max-h-none print:overflow-visible">
            {report.transcript.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-1.5 text-xs ${
                    m.role === "user" ? "bg-indigo-600 text-white" : "border border-slate-200 bg-white text-slate-700"
                  } print:border print:border-slate-300 print:bg-white print:text-slate-800`}
                >
                  {m.content}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
