import { Badge } from "@/components/ui/Badge";
import { IconAlert, IconCheck, IconFile, IconSparkle } from "@/components/icons";
import type { AssessmentGroupScore, AssessmentReport, ChatReport, FiveC } from "@/lib/api";
import {
  ANSWER_GROUPS,
  RISK_TONE,
  TIER,
  type Tone,
  fmtAnswer,
  fmtDateTime,
  fmtMetric,
  fmtScore,
  humanize,
  metricLabel,
} from "./format";

// Sections of the staff application report (app/staff/applications/[id]/report).
// Ordered for the officer's task: the recommendation and anything blocking
// first, the evidence behind it on demand.

const FIVE_C_ORDER: FiveC[] = ["capacity", "capital", "character", "collateral", "conditions"];

const FIVE_C_META: Record<FiveC, { label: string; blurb: string }> = {
  capacity: { label: "Capacity", blurb: "Ability to service the repayments" },
  capital: { label: "Capital", blurb: "Deposit, savings and net assets" },
  character: { label: "Character", blurb: "Credit history and conduct" },
  collateral: { label: "Collateral", blurb: "Security offered for the loan" },
  conditions: { label: "Conditions", blurb: "Purpose, structure and context" },
};

const TONE_TEXT: Record<Tone, string> = {
  slate: "text-slate-700",
  indigo: "text-indigo-700",
  emerald: "text-emerald-700",
  amber: "text-amber-700",
  red: "text-red-700",
};

const TONE_ACCENT: Record<Tone, string> = {
  slate: "border-l-slate-300",
  indigo: "border-l-indigo-500",
  emerald: "border-l-emerald-500",
  amber: "border-l-amber-500",
  red: "border-l-red-500",
};

function scoreTone(score: number): Tone {
  if (score >= 80) return "emerald";
  if (score >= 60) return "amber";
  return "red";
}

const BAR_FILL: Record<Tone, string> = {
  slate: "bg-slate-400",
  indigo: "bg-indigo-500",
  emerald: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

function ScoreBar({ score, label }: { score: number; label: string }) {
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuenow={score}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 print:border print:border-slate-200"
    >
      <div className={`h-full rounded-full ${BAR_FILL[scoreTone(score)]}`} style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }} />
    </div>
  );
}

export function SectionHeading({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-sm font-semibold text-slate-900">{children}</h2>
      {action}
    </div>
  );
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/50 print:break-inside-avoid print:shadow-none ${className}`}>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------- summary --

function Tile({ label, value, caption, tone = "slate", children }: {
  label: string;
  value: React.ReactNode;
  caption?: React.ReactNode;
  tone?: Tone;
  children?: React.ReactNode;
}) {
  return (
    <div className={`rounded-2xl border border-l-4 border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/50 print:shadow-none ${TONE_ACCENT[tone]}`}>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-semibold tracking-tight ${tone === "slate" ? "text-slate-900" : TONE_TEXT[tone]}`}>{value}</p>
      {children}
      {caption && <p className="mt-1 text-xs text-slate-400">{caption}</p>}
    </div>
  );
}

export function SummaryTiles({ assessment, creditScore }: { assessment: AssessmentReport; creditScore: number | null }) {
  const tier = TIER[assessment.tier] ?? { label: humanize(assessment.tier), tone: "slate" as Tone, hint: "" };
  const factors = assessment.risk_profile.factors.length;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile label="Recommendation" value={tier.label} caption={tier.hint} tone={tier.tone} />
      <Tile
        label="Weighted score"
        value={
          <>
            {fmtScore(assessment.overall_score)}
            <span className="text-sm font-normal text-slate-400"> / 100</span>
          </>
        }
        caption={`${assessment.metrics_computed} of ${assessment.metrics_total} metrics computed`}
        tone={assessment.overall_score === null ? "slate" : scoreTone(assessment.overall_score)}
      >
        {assessment.overall_score !== null && (
          <div className="mt-2">
            <ScoreBar score={assessment.overall_score} label="Weighted score" />
          </div>
        )}
      </Tile>
      <Tile
        label="Risk"
        value={humanize(assessment.risk_profile.category)}
        caption={factors === 0 ? "No risk factors noted" : `${factors} risk factor${factors === 1 ? "" : "s"} noted`}
        tone={RISK_TONE[assessment.risk_profile.category] ?? "slate"}
      />
      <Tile
        label="Credit score"
        value={
          creditScore === null ? (
            "—"
          ) : (
            <>
              {creditScore.toLocaleString()}
              <span className="text-sm font-normal text-slate-400"> / 1200</span>
            </>
          )
        }
        caption={creditScore === null ? "No bureau report on file" : "From the credit bureau"}
      />
    </div>
  );
}

export function NarrativePanel({ text }: { text: string }) {
  return (
    <Panel className="h-full">
      <SectionHeading>
        <span className="inline-flex items-center gap-2">
          <IconSparkle className="h-4 w-4 text-indigo-500" />
          Summary
        </span>
      </SectionHeading>
      <p className="text-sm leading-6 text-slate-700">{text}</p>
      <p className="mt-3 text-xs text-slate-400">Generated from the assessment — check it against the figures below.</p>
    </Panel>
  );
}

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 } as const;

export function AttentionPanel({ assessment }: { assessment: AssessmentReport }) {
  const conditions = [...assessment.conditions_of_approval].sort((a, b) => Number(b.blocking) - Number(a.blocking));
  const factors = [...assessment.risk_profile.factors].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  return (
    <Panel className="h-full">
      <SectionHeading>Before you decide</SectionHeading>
      {conditions.length === 0 && factors.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-emerald-700">
          <IconCheck className="h-4 w-4" />
          No conditions or risk factors flagged.
        </p>
      ) : (
        <ul className="space-y-3">
          {conditions.map((c) => (
            <li key={c.id} className="flex gap-2.5">
              <IconAlert className={`mt-0.5 h-4 w-4 shrink-0 ${c.blocking ? "text-red-500" : "text-amber-500"}`} />
              <div className="min-w-0">
                <p className="text-sm text-slate-800">{c.text}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {c.blocking ? "Condition of approval" : "Advisory"} · {c.reason}
                </p>
              </div>
            </li>
          ))}
          {factors.map((f, i) => (
            <li key={i} className="flex gap-2.5">
              <span
                className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                  f.severity === "high" ? "bg-red-500" : f.severity === "medium" ? "bg-amber-500" : "bg-slate-300"
                }`}
              />
              <div className="min-w-0">
                <p className="text-sm text-slate-800">{f.label}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {humanize(f.severity)} risk · {f.detail}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

// ------------------------------------------------------------- assessment --

function FiveCCard({ fiveC, group, weight, completeness }: {
  fiveC: FiveC;
  group?: AssessmentGroupScore;
  weight?: number;
  completeness?: string;
}) {
  const meta = FIVE_C_META[fiveC];
  const scored = group && group.state === "computed" && group.score !== null;

  return (
    <div className="flex flex-col rounded-xl border border-slate-200/80 p-4 print:break-inside-avoid">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{meta.label}</p>
          <p className="text-xs text-slate-400">
            {meta.blurb}
            {weight !== undefined && ` · ${weight}% of score`}
          </p>
        </div>
        <p className={`text-2xl font-semibold tabular-nums ${scored ? TONE_TEXT[scoreTone(group.score!)] : "text-slate-300"}`}>
          {scored ? group.score!.toFixed(0) : "—"}
        </p>
      </div>

      {scored ? (
        <>
          <div className="mt-3">
            <ScoreBar score={group.score!} label={`${meta.label} score`} />
          </div>
          <dl className="mt-3 space-y-1.5 text-xs">
            {group.metrics_used.map((m) => (
              <div key={m.metric} className="flex items-baseline justify-between gap-3">
                <dt className="text-slate-500">{metricLabel(m.metric)}</dt>
                <dd className="text-right tabular-nums text-slate-800">{fmtMetric(m.raw_value, m.unit)}</dd>
              </div>
            ))}
            {group.metrics_skipped.map((m) => (
              <div key={m.metric} className="flex items-baseline justify-between gap-3 text-slate-400">
                <dt>{metricLabel(m.metric)}</dt>
                <dd className="text-right italic">{humanize(m.reason)}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : (
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
          {completeness === "not_applicable"
            ? "Not applicable to this product."
            : "Not scored — not enough information was provided for this area."}
        </p>
      )}
    </div>
  );
}

export function AssessmentPanel({ assessment, chat }: { assessment: AssessmentReport; chat: ChatReport | null }) {
  const allMetrics = chat?.assessment ? Object.entries(chat.assessment.metrics) : [];
  const ruleTier = TIER[assessment.rule_based_indicator.tier]?.label ?? humanize(assessment.rule_based_indicator.tier);

  return (
    <div className="space-y-6">
      <Panel>
        <SectionHeading>Five C&apos;s breakdown</SectionHeading>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {FIVE_C_ORDER.map((c) => (
            <FiveCCard
              key={c}
              fiveC={c}
              group={assessment.group_scores[c]}
              weight={assessment.weights_applied[c]}
              completeness={assessment.data_completeness[c]}
            />
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-400">
          Rule engine cross-check: {ruleTier} ({assessment.rule_based_indicator.fail_count} fail,{" "}
          {assessment.rule_based_indicator.flag_count} flag, {assessment.rule_based_indicator.provisional_count}{" "}
          provisional). The weighted score is the recommendation.
        </p>
      </Panel>

      <div className="grid grid-cols-1 gap-6 items-start lg:grid-cols-2">
        {assessment.policy_comparison.length > 0 && (
          <Panel>
            <SectionHeading>Policy checks</SectionHeading>
            <ul className="divide-y divide-slate-100">
              {assessment.policy_comparison.map((cmp) => (
                <li key={cmp.metric} className="flex items-start justify-between gap-4 py-2.5 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="text-sm text-slate-800">{cmp.label}</p>
                    <p className="text-xs text-slate-400">
                      {cmp.threshold_label}: {fmtMetric(cmp.threshold, cmp.unit)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-sm font-medium tabular-nums text-slate-900">{fmtMetric(cmp.value, cmp.unit)}</span>
                    <Badge tone={cmp.meets_threshold ? "emerald" : "red"}>{cmp.meets_threshold ? "Pass" : "Fail"}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
        )}

        {assessment.key_figures.length > 0 && (
          <Panel>
            <SectionHeading>Key figures</SectionHeading>
            <dl className="divide-y divide-slate-100">
              {assessment.key_figures.map((f) => (
                <div key={f.metric} className="flex items-baseline justify-between gap-4 py-2 text-sm first:pt-0 last:pb-0">
                  <dt className="text-slate-500">{f.label}</dt>
                  <dd className="text-right font-medium tabular-nums text-slate-900">{fmtMetric(f.value, f.unit)}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        )}
      </div>

      {allMetrics.length > 0 && (
        <details className="group rounded-2xl border border-slate-200/80 bg-white shadow-sm shadow-slate-200/50 print:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-sm font-semibold text-slate-900">
            All metrics ({allMetrics.length})
            <span className="text-xs font-normal text-slate-400 group-open:hidden">Show for audit</span>
            <span className="hidden text-xs font-normal text-slate-400 group-open:inline">Hide</span>
          </summary>
          <dl className="grid grid-cols-1 gap-x-8 border-t border-slate-100 px-5 py-4 text-xs md:grid-cols-2">
            {allMetrics.map(([key, m]) => (
              <div key={key} className="flex items-baseline justify-between gap-3 border-b border-slate-50 py-1.5">
                <dt className="text-slate-500">{metricLabel(key)}</dt>
                <dd className="text-right tabular-nums">
                  {m.state === "computed" ? (
                    <span className="text-slate-800">{fmtMetric(m.value, m.unit)}</span>
                  ) : (
                    <span className="italic text-slate-400">{humanize(m.state)}</span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </div>
  );
}

// -------------------------------------------------------------- applicant --

export function ApplicantPanel({ chat }: { chat: ChatReport }) {
  const byGroup = new Map<string, ChatReport["slots"]>();
  for (const slot of chat.slots) {
    const group = slot.group ?? "other";
    byGroup.set(group, [...(byGroup.get(group) ?? []), slot]);
  }
  const groups = [...ANSWER_GROUPS, { id: "other", label: "Other" }].filter((g) => byGroup.has(g.id));

  if (groups.length === 0) {
    return <Panel><p className="text-sm text-slate-400">No interview answers recorded.</p></Panel>;
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {groups.map((g) => (
        <Panel key={g.id}>
          <SectionHeading>{g.label}</SectionHeading>
          <dl className="divide-y divide-slate-100">
            {byGroup.get(g.id)!.map((s) => (
              <div key={s.slot_key} className="flex items-baseline justify-between gap-4 py-2 text-sm first:pt-0 last:pb-0">
                <dt className="text-slate-500">{s.label ?? humanize(s.slot_key)}</dt>
                <dd className="text-right font-medium text-slate-900">{fmtAnswer(s.value, s.type)}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      ))}
    </div>
  );
}

// -------------------------------------------------------------- documents --

const DOC_STATUS: Record<string, { label: string; tone: Tone }> = {
  extracted: { label: "Verified", tone: "emerald" },
  needs_reupload: { label: "Needs re-upload", tone: "red" },
  uploaded: { label: "Processing", tone: "slate" },
};

export function DocumentsPanel({ chat }: { chat: ChatReport }) {
  if (chat.documents.length === 0) {
    return (
      <Panel>
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <IconFile className="h-8 w-8 text-slate-300" />
          <p className="text-sm text-slate-500">No documents uploaded.</p>
        </div>
      </Panel>
    );
  }
  return (
    <Panel>
      <ul className="divide-y divide-slate-100">
        {chat.documents.map((d) => {
          const status = DOC_STATUS[d.status] ?? { label: humanize(d.status), tone: "slate" as Tone };
          return (
            <li key={d.document_id} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 gap-3">
                  <IconFile className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900">{humanize(d.verification_type)}</p>
                    <p className="truncate text-xs text-slate-400">
                      {d.original_filename} · {fmtDateTime(d.uploaded_at)}
                    </p>
                  </div>
                </div>
                <Badge tone={status.tone}>{status.label}</Badge>
              </div>
              {d.verifications.length > 0 && (
                <dl className="ml-8 mt-2 space-y-1 text-xs">
                  {d.verifications.map((v, i) => (
                    <div key={i} className="flex flex-wrap items-baseline gap-x-2">
                      <dt className="text-slate-500">{humanize(v.slot_id)}:</dt>
                      <dd className="text-slate-700">
                        declared {v.declared_value}, document shows {v.extracted_value}{" "}
                        <span className={v.status === "match" ? "text-emerald-600" : "text-amber-600"}>
                          ({v.status === "match" ? "matches" : humanize(v.status).toLowerCase()})
                        </span>
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

// ----------------------------------------------------------- conversation --

export function ConversationPanel({ chat }: { chat: ChatReport }) {
  if (chat.transcript.length === 0) {
    return <Panel><p className="text-sm text-slate-400">No conversation recorded.</p></Panel>;
  }
  return (
    <Panel>
      <ol className="space-y-3">
        {chat.transcript.map((m, i) => {
          const fromApplicant = m.role === "user";
          return (
            <li key={i} className={`flex ${fromApplicant ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[80%]">
                <p className={`mb-1 text-[11px] text-slate-400 ${fromApplicant ? "text-right" : ""}`}>
                  {fromApplicant ? "Applicant" : "Assistant"} · {fmtDateTime(m.created_at)}
                </p>
                <div
                  className={`rounded-2xl px-3.5 py-2 text-sm ${
                    fromApplicant ? "bg-indigo-600 text-white" : "border border-slate-200 bg-slate-50 text-slate-700"
                  } print:border print:border-slate-300 print:bg-white print:text-slate-800`}
                >
                  {m.content}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}
