import type { ReactNode } from "react";
import { useState } from "react";
import { IBM_Plex_Mono } from "next/font/google";
import { BudgetWaterfall, FiveCRadar } from "./ReportCharts";
import type { AssessmentReport, BankPolicyCheckStatus, ChatReport, FiveC, LoanApplicationOut } from "@/lib/api";
import {
  ANSWER_GROUPS,
  TIER,
  fmtAnswer,
  fmtDate,
  fmtDateTime,
  fmtMetric,
  fmtMoney,
  fmtScore,
  humanize,
  metricLabel,
  statusLabel,
} from "./format";



const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"] });

export const ui = {
  panel: "rounded-[4px] border border-[#d6d9de] bg-white print:break-inside-avoid",
  panelTitle: "text-[14px] font-semibold text-[#1b1e23]",
  label: "text-[12px] text-[#5d6470]",
  muted: "text-[#8a909a]",
  brandButton:
    "inline-flex items-center justify-center rounded-[4px] bg-[#1f5fa8] px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-[#164a85] disabled:opacity-50",
  outlineButton:
    "inline-flex items-center px-3.5 py-1.5 text-[13px] text-[#1f5fa8] transition-colors hover:bg-[#f3f6fa] disabled:opacity-50",
};

const TIER_PILL: Record<string, string> = {
  emerald: "bg-[#e6f4ea] text-[#2e844a]",
  amber: "bg-[#fdf3e1] text-[#8c5a00]",
  red: "bg-[#fbe9e8] text-[#c23934]",
  slate: "bg-[#eef0f3] text-[#5d6470]",
  indigo: "bg-[#e3ecf7] text-[#1f5fa8]",
};

export function Pill({ tone, children }: { tone: keyof typeof TIER_PILL; children: ReactNode }) {
  return <span className={`inline-flex items-center whitespace-nowrap rounded-[3px] px-2 py-0.5 text-[12px] font-medium ${TIER_PILL[tone]}`}>{children}</span>;
}

function PanelHeader({ title, aside }: { title: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[#e3e6ea] px-4 py-3">
      <h2 className={ui.panelTitle}>{title}</h2>
      {aside && <div className={`text-[12px] ${ui.muted}`}>{aside}</div>}
    </div>
  );
}


export function RecordHeader({
  applicantName,
  accountName,
  application,
  assessment,
  chat,
  actions,
}: {
  applicantName: string;
  accountName?: string | null;
  application: LoanApplicationOut | null;
  assessment: AssessmentReport | null;
  chat: ChatReport | null;
  actions: ReactNode;
}) {
  const facts = new Map(assessment?.applicant_summary.map((f) => [f.id, f.value]) ?? []);
  const term = facts.get("loan_term_months") as number | undefined;
  const reference = application?.id.split("-")[0].toUpperCase();

  const fields: { label: string; value: ReactNode }[] = [
    { label: "Application number", value: reference ? <span className={mono.className}>{reference}</span> : "—" },
    { label: "Applicant", value: <span className="text-[#1f5fa8]">{applicantName}</span> },
    ...(accountName && accountName.trim().toLowerCase() !== applicantName.trim().toLowerCase()
      ? [{ label: "Login account", value: accountName }]
      : []),
    { label: "Requested amount", value: application ? fmtMoney(application.requested_amount) : "—" },
    { label: "Requested term", value: term ? `${term} months` : "—" },
    { label: "Product", value: assessment?.product_name ?? chat?.product_code ?? "—" },
    { label: "Status", value: application ? statusLabel(application.status) : "—" },
    { label: "Submitted", value: application ? fmtDate(application.created_at) : "—" },
  ];

  return (
    <div className={ui.panel}>
      <div className="flex flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] bg-[#1f5fa8] text-white">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 20V9l8-5 8 5v11M9 20v-6h6v6M3 20h18" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <div className="min-w-0">
            <p className={ui.label}>Loan Application</p>
            <h1 className="truncate text-[20px] font-semibold leading-tight text-[#1b1e23]">
              {applicantName}
              {reference && <span className="font-normal text-[#5d6470]"> – {reference}</span>}
            </h1>
          </div>
        </div>
        <div className="flex shrink-0 divide-x divide-[#cfd3d9] overflow-hidden rounded-[4px] border border-[#cfd3d9] print:hidden">
          {actions}
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-8 gap-y-3 border-t border-[#e3e6ea] px-4 py-3 sm:grid-cols-4 xl:flex xl:gap-10">
        {fields.map((f) => (
          <div key={f.label} className="min-w-0">
            <dt className={ui.label}>{f.label}</dt>
            <dd className="mt-0.5 truncate text-[14px] text-[#1b1e23]">{f.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// -------------------------------------------------------------- stage bar --

const STAGES = ["Interview", "Documents", "Assessment", "Credit review", "Decision"];

function stageIndex(application: LoanApplicationOut | null, chat: ChatReport | null): number {
  const decided = application && ["approved", "rejected", "disbursed"].includes(application.status);
  if (decided || chat?.decision) return STAGES.length;
  if (application) return 3;
  return { interview: 0, documents: 1, assessment: 2 }[chat?.status ?? ""] ?? 0;
}

export function StageBar({ application, chat }: { application: LoanApplicationOut | null; chat: ChatReport | null }) {
  const current = stageIndex(application, chat);
  const outcome = application?.status === "rejected" ? "Declined" : application?.status === "approved" ? "Approved" : null;

  return (
    <div className={`${ui.panel} px-3 py-2.5`}>
      <ol className="flex">
        {STAGES.map((stage, i) => {
          const done = i < current;
          const active = i === current;
          const label = i === STAGES.length - 1 && outcome ? outcome : stage;
          const colour =
            i === STAGES.length - 1 && outcome === "Declined" && done
              ? "bg-[#c23934] text-white"
              : done
                ? "bg-[#2e844a] text-white"
                : active
                  ? "bg-[#16325c] font-semibold text-white"
                  : "bg-[#e5e8ec] text-[#343a42]";
          return (
            <li
              key={stage}
              aria-current={active ? "step" : undefined}
              className={`relative flex h-8 min-w-0 flex-1 items-center justify-center text-[13px] print:border print:border-[#d6d9de] ${colour}`}
              style={{
                clipPath:
                  i === 0
                    ? "polygon(0 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 0 100%)"
                    : i === STAGES.length - 1
                      ? "polygon(0 0, 100% 0, 100% 100%, 0 100%, 12px 50%)"
                      : "polygon(0 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 0 100%, 12px 50%)",
                marginLeft: i === 0 ? 0 : -8,
                borderRadius: i === 0 ? "16px 0 0 16px" : i === STAGES.length - 1 ? "0 16px 16px 0" : undefined,
              }}
            >
              <span className="truncate px-5" title={label}>
                {done && i !== STAGES.length - 1 ? "✓ " : ""}
                {/* Narrow screens name only the current stage; the rest show a tick or step number. */}
                <span className={active ? "" : "hidden md:inline"}>{label}</span>
                {!active && !done && <span className="md:hidden">{i + 1}</span>}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// ------------------------------------------------------------------- tabs --

export function RecordTabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onChange: (id: T) => void;
}) {
  function onKeyDown(e: React.KeyboardEvent, index: number) {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = tabs[(index + step + tabs.length) % tabs.length];
    onChange(next.id);
    document.getElementById(`tab-${next.id}`)?.focus();
  }

  return (
    <div role="tablist" aria-label="Report sections" className="flex gap-1 overflow-x-auto border-b border-[#e3e6ea] px-3 print:hidden">
      {tabs.map((t, i) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={selected}
            aria-controls={`panel-${t.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={`-mb-px shrink-0 border-b-[3px] px-3 py-3 text-[14px] transition-colors focus:outline-none focus-visible:bg-[#f3f6fa] ${
              selected ? "border-[#1f5fa8] font-semibold text-[#1b1e23]" : "border-transparent text-[#343a42] hover:text-[#1f5fa8]"
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[#8a909a]">({t.count})</span>}
          </button>
        );
      })}
    </div>
  );
}


function Section({ title, aside, defaultOpen = true, children }: {
  title: string;
  aside?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="border-b border-[#e3e6ea] last:border-b-0">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="flex items-center gap-2 text-[14px] text-[#1b1e23] hover:text-[#1f5fa8]"
        >
          <span className={`inline-block text-[10px] text-[#5d6470] transition-transform ${open ? "rotate-90" : ""}`}>▶</span>
          {title}
        </button>
        {aside}
      </div>
      <div className={open ? "px-4 pb-4 pl-10" : "hidden print:block print:px-4 print:pb-4 print:pl-10"}>{children}</div>
    </section>
  );
}

function FieldGrid({ fields }: { fields: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
      {fields.map((f, i) => (
        <div key={`${f.label}-${i}`} className="border-b border-[#e3e6ea] py-2">
          <dt className={ui.label}>{f.label}</dt>
          <dd className="mt-0.5 text-[14px] text-[#1b1e23]">{f.value}</dd>
        </div>
      ))}
    </dl>
  );
}


const FIVE_C_ORDER: FiveC[] = ["capacity", "capital", "character", "collateral", "conditions"];
const FIVE_C_LABEL: Record<FiveC, string> = {
  capacity: "Capacity — ability to repay",
  capital: "Capital — savings and net assets",
  character: "Character — credit history",
  collateral: "Collateral — security offered",
  conditions: "Conditions — purpose and context",
};

function KpiStrip({ assessment, creditScore }: { assessment: AssessmentReport; creditScore: number | null }) {
  const tier = TIER[assessment.tier] ?? { label: humanize(assessment.tier), tone: "slate" as const, hint: "" };
  const cells = assessment.policy_comparison.slice(0, 3).map((p) => ({
    label: p.label,
    value: fmtMetric(p.value, p.unit),
    note: `${p.threshold_label.replace(/ \(.*\)$/, "")}: ${fmtMetric(p.threshold, p.unit)}`,
    ok: p.meets_threshold,
  }));

  return (
    <div className="grid grid-cols-2 border-b border-[#e3e6ea] md:grid-cols-4">
      <div className="col-span-full flex items-center gap-3 border-b border-[#e3e6ea] p-4">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[4px] bg-[#1f5fa8] text-[18px] font-semibold text-white">
          {fmtScore(assessment.overall_score)}
        </span>
        <div className="min-w-0">
          <p className={ui.label}>Recommendation</p>
          <p className="text-[14px] font-semibold text-[#1b1e23]">{tier.label}</p>
          <p className={`text-[12px] ${ui.muted}`}>
            {humanize(assessment.risk_profile.category)} risk · score {fmtScore(assessment.overall_score)} / 100
          </p>
        </div>
      </div>
      <div className="border-b border-r border-[#e3e6ea] p-4 md:border-b-0">
        <p className={ui.label}>Credit score</p>
        <p className="mt-1 text-[22px] font-medium tabular-nums text-[#1b1e23]">{creditScore ?? "—"}</p>
        <p className={`text-[12px] ${ui.muted}`}>Bureau, out of 1,200</p>
      </div>
      {cells.map((c) => (
        <div key={c.label} className="border-r border-[#e3e6ea] p-4 last:border-r-0 [&:nth-child(3)]:border-b md:[&:nth-child(3)]:border-b-0">
          <p className={ui.label}>{c.label}</p>
          <p className="mt-1 text-[22px] font-medium tabular-nums text-[#1b1e23]">{c.value}</p>
          <p className={`text-[12px] ${c.ok ? "text-[#2e844a]" : "text-[#c23934]"}`}>{c.note}</p>
        </div>
      ))}
    </div>
  );
}

function Scorecard({ assessment }: { assessment: AssessmentReport }) {
  const tier = TIER[assessment.tier]?.label ?? humanize(assessment.tier);
  return (
    <div className={ui.panel}>
      <PanelHeader title="Scorecard" aside="Weighted score out of 100" />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-[14px]">
          <thead>
            <tr className="border-b border-[#e3e6ea] bg-[#f7f8fa] text-left text-[12px] text-[#5d6470]">
              <th className="px-4 py-2 font-medium">Factor</th>
              <th className="px-4 py-2 text-right font-medium">Weight</th>
              <th className="px-4 py-2 text-right font-medium">Score</th>
              <th className="w-[40%] px-4 py-2 font-medium">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {FIVE_C_ORDER.map((c) => {
              const group = assessment.group_scores[c];
              const scored = group && group.state === "computed" && group.score !== null;
              const weight = assessment.weights_applied[c];
              return (
                <tr key={c} className="border-b border-[#e3e6ea]">
                  <td className="px-4 py-2.5 text-[#1b1e23]">{humanize(c)}</td>
                  <td className={`px-4 py-2.5 text-right tabular-nums ${mono.className} text-[13px] text-[#5d6470]`}>
                    {weight !== undefined ? `${weight}%` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right font-semibold tabular-nums text-[#1b1e23]">
                    {scored ? group.score!.toFixed(0) : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    {scored ? (
                      <div className="h-2 w-full bg-[#e5e8ec]">
                        <div
                          className={`h-full ${group.score! >= 60 ? "bg-[#1f5fa8]" : "bg-[#c9a227]"}`}
                          style={{ width: `${Math.min(group.score!, 100)}%` }}
                        />
                      </div>
                    ) : (
                      <span className={`text-[12px] ${ui.muted}`}>
                        {assessment.data_completeness[c] === "not_applicable" ? "Not applicable" : "Not scored — insufficient data"}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            <tr className="bg-[#f7f8fa] font-semibold">
              <td className="px-4 py-2.5">Total</td>
              <td className="px-4 py-2.5 text-right tabular-nums">100%</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{fmtScore(assessment.overall_score)}</td>
              <td className="px-4 py-2.5 text-[#1f5fa8]">{tier}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className={`px-4 py-2.5 text-[12px] ${ui.muted}`}>
        Rule engine cross-check: {TIER[assessment.rule_based_indicator.tier]?.label ?? humanize(assessment.rule_based_indicator.tier)} —{" "}
        {assessment.rule_based_indicator.fail_count} fail, {assessment.rule_based_indicator.flag_count} flag,{" "}
        {assessment.rule_based_indicator.provisional_count} provisional.
      </p>
    </div>
  );
}

function PolicyChecks({ assessment }: { assessment: AssessmentReport }) {
  const checks = assessment.policy_comparison;
  if (checks.length === 0) return null;
  const exceptions = checks.filter((c) => !c.meets_threshold).length;
  return (
    <div className={ui.panel}>
      <PanelHeader
        title="Policy checks"
        aside={`${checks.length - exceptions} pass · ${exceptions} exception${exceptions === 1 ? "" : "s"}`}
      />
      <ul>
        {checks.map((c) => (
          <li
            key={c.metric}
            className={`flex items-center justify-between gap-4 border-b border-[#e3e6ea] px-4 py-2.5 text-[14px] last:border-b-0 ${
              c.meets_threshold ? "" : "bg-[#fdf6e7]"
            }`}
          >
            <div className="min-w-0">
              <p className="text-[#1b1e23]">{c.label}</p>
              <p className={`text-[12px] ${ui.muted}`}>
                {c.threshold_label}: {fmtMetric(c.threshold, c.unit)} · actual {fmtMetric(c.value, c.unit)}
              </p>
            </div>
            <span className={`shrink-0 font-medium ${c.meets_threshold ? "text-[#2e844a]" : "text-[#8c5a00]"}`}>
              {c.meets_threshold ? "Pass" : "Exception"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const BANK_POLICY_STATUS: Record<BankPolicyCheckStatus, { label: string; tone: keyof typeof TIER_PILL; row: string }> = {
  pass: { label: "Pass", tone: "emerald", row: "" },
  exception: { label: "Exception", tone: "red", row: "bg-[#fdf1f0]" },
  review: { label: "Review", tone: "amber", row: "bg-[#fdf6e7]" },
  no_data: { label: "No data", tone: "slate", row: "" },
  not_applicable: { label: "N/A", tone: "slate", row: "" },
};

function BankPolicyCheckCard({ assessment }: { assessment: AssessmentReport }) {
  const result = assessment.bank_policy_check;
  if (!result) return null;
  const { summary } = result;

  return (
    <div className={ui.panel}>
      <PanelHeader
        title="Bank policy check"
        aside={
          result.status === "ok"
            ? `${summary.pass} pass · ${summary.exception} exception${summary.exception === 1 ? "" : "s"} · ${summary.review} to review`
            : undefined
        }
      />
      {result.status === "ok" ? (
        <>
          <ul>
            {result.checks.map((c) => {
              const status = BANK_POLICY_STATUS[c.status];
              return (
                <li
                  key={c.category}
                  className={`flex items-start justify-between gap-4 border-b border-[#e3e6ea] px-4 py-2.5 text-[14px] last:border-b-0 ${status.row}`}
                >
                  <div className="min-w-0">
                    <p className="text-[#1b1e23]">
                      {c.label}
                      {c.applicant_value && <span className="text-[#5d6470]"> · {c.applicant_value}</span>}
                    </p>
                    <p className="text-[12px] text-[#343a42]">{c.detail}</p>
                    <p className={`text-[12px] ${ui.muted}`}>Policy: {c.policy_rule}</p>
                  </div>
                  <Pill tone={status.tone}>{status.label}</Pill>
                </li>
              );
            })}
          </ul>
          <p className={`border-t border-[#e3e6ea] px-4 py-2.5 text-[12px] ${ui.muted}`}>
            Checked against {result.bank} · {result.loan_type} ({result.source}, demo policy data). For reference only. It does not
            change the score or the recommendation.
          </p>
        </>
      ) : (
        <p className={`px-4 py-3 text-[13px] ${ui.muted}`}>
          {result.status === "not_loaded"
            ? "Bank policy data has not been loaded yet. Run the policy ingest step from the README."
            : `No bank policy found for ${result.loan_type ?? "this product"} at ${result.bank}.`}
        </p>
      )}
    </div>
  );
}

function KeyFigures({ assessment }: { assessment: AssessmentReport }) {
  if (assessment.key_figures.length === 0) return null;
  return (
    <div className={ui.panel}>
      <PanelHeader title="Serviceability" />
      <table className="w-full text-[14px]">
        <tbody>
          {assessment.key_figures.map((f) => (
            <tr key={f.metric} className="border-b border-[#e3e6ea] last:border-b-0">
              <td className="px-4 py-2 text-[#343a42]">{f.label}</td>
              <td className="whitespace-nowrap px-4 py-2 text-right tabular-nums text-[#1b1e23]">
                {fmtMetric(f.value, f.unit)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CreditAssessmentTab({
  assessment,
  chat,
  creditScore,
}: {
  assessment: AssessmentReport;
  chat: ChatReport | null;
  creditScore: number | null;
}) {
  const allMetrics = chat?.assessment ? Object.entries(chat.assessment.metrics) : [];
  return (
    <div>
      <KpiStrip assessment={assessment} creditScore={creditScore} />
      <div className="space-y-4 p-4">
        <div className="grid grid-cols-1 items-stretch gap-4 xl:grid-cols-2">
          <div className={ui.panel}>
            <PanelHeader title="Five C's profile" aside="Score out of 100" />
            <div className="p-4">
              <FiveCRadar assessment={assessment} />
            </div>
          </div>
          <div className={ui.panel}>
            <PanelHeader title="Monthly budget" aside="After the new repayment" />
            <div className="p-4">
              <BudgetWaterfall assessment={assessment} />
            </div>
          </div>
        </div>
        <Scorecard assessment={assessment} />
        <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
          <PolicyChecks assessment={assessment} />
          <KeyFigures assessment={assessment} />
        </div>
        <BankPolicyCheckCard assessment={assessment} />
      </div>
      <div className="border-t border-[#e3e6ea]">
        {FIVE_C_ORDER.map((c) => {
          const group = assessment.group_scores[c];
          const rows = [
            ...(group?.metrics_used ?? []).map((m) => ({ label: metricLabel(m.metric), value: fmtMetric(m.raw_value, m.unit) })),
            ...(group?.metrics_skipped ?? []).map((m) => ({
              label: metricLabel(m.metric),
              value: <span className={`italic ${ui.muted}`}>{humanize(m.reason)}</span>,
            })),
          ];
          return (
            <Section
              key={c}
              title={FIVE_C_LABEL[c]}
              aside={
                group?.state === "computed" && group.score !== null ? (
                  <span className="text-[13px] font-semibold tabular-nums text-[#1b1e23]">{group.score.toFixed(0)}</span>
                ) : (
                  <span className={`text-[12px] ${ui.muted}`}>Not scored</span>
                )
              }
            >
              {rows.length > 0 ? <FieldGrid fields={rows} /> : <p className={`text-[13px] ${ui.muted}`}>No metrics for this factor.</p>}
            </Section>
          );
        })}
        {allMetrics.length > 0 && (
          <div className="print:hidden">
            <Section title={`All metrics (${allMetrics.length}) — audit view`} defaultOpen={false}>
              <FieldGrid
                fields={allMetrics.map(([key, m]) => ({
                  label: metricLabel(key),
                  value: m.state === "computed" ? fmtMetric(m.value, m.unit) : <span className={`italic ${ui.muted}`}>{humanize(m.state)}</span>,
                }))}
              />
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}


export function ApplicantTab({ chat }: { chat: ChatReport }) {
  const byGroup = new Map<string, ChatReport["slots"]>();
  for (const slot of chat.slots) {
    const group = slot.group ?? "other";
    byGroup.set(group, [...(byGroup.get(group) ?? []), slot]);
  }
  const groups = [...ANSWER_GROUPS, { id: "other", label: "Other" }].filter((g) => byGroup.has(g.id));
  if (groups.length === 0) return <p className={`p-4 text-[14px] ${ui.muted}`}>No interview answers recorded.</p>;

  return (
    <div>
      {groups.map((g) => (
        <Section key={g.id} title={g.label}>
          <FieldGrid
            fields={byGroup.get(g.id)!.map((s) => ({ label: s.label ?? humanize(s.slot_key), value: fmtAnswer(s.value, s.type) }))}
          />
        </Section>
      ))}
    </div>
  );
}


export function ConversationTab({ chat }: { chat: ChatReport }) {
  if (chat.transcript.length === 0) return <p className={`p-4 text-[14px] ${ui.muted}`}>No conversation recorded.</p>;
  return (
    <ol className="divide-y divide-[#e3e6ea]">
      {chat.transcript.map((m, i) => (
        <li key={i} className="grid grid-cols-[110px_1fr] gap-4 px-4 py-3 text-[14px]">
          <div>
            <p className={`font-medium ${m.role === "user" ? "text-[#1f5fa8]" : "text-[#1b1e23]"}`}>
              {m.role === "user" ? "Applicant" : "Assistant"}
            </p>
            <p className={`text-[12px] ${ui.muted}`}>{fmtDateTime(m.created_at)}</p>
          </div>
          <p className="whitespace-pre-wrap text-[#343a42]">{m.content}</p>
        </li>
      ))}
    </ol>
  );
}


export function RecommendationPanel({ assessment }: { assessment: AssessmentReport }) {
  const tier = TIER[assessment.tier] ?? { label: humanize(assessment.tier), tone: "slate" as const, hint: "" };
  return (
    <div className={ui.panel}>
      <PanelHeader title="Recommendation" aside={<Pill tone={tier.tone}>{tier.label}</Pill>} />
      {assessment.narrative_summary ? (
        <p className="px-4 py-3 text-[14px] leading-6 text-[#343a42]">{assessment.narrative_summary}</p>
      ) : (
        <div className="space-y-2 px-4 py-4" aria-live="polite">
          <p className="flex items-center gap-2 text-[13px] text-[#5d6470]">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#cfd3d9] border-t-[#1f5fa8]" />
            Writing AI recommendation…
          </p>
          <div className="h-2.5 w-full animate-pulse rounded bg-[#e5e8ec]" />
          <div className="h-2.5 w-11/12 animate-pulse rounded bg-[#e5e8ec]" />
          <div className="h-2.5 w-3/4 animate-pulse rounded bg-[#e5e8ec]" />
        </div>
      )}
      <p className={`border-t border-[#e3e6ea] px-4 py-2 text-[12px] ${ui.muted}`}>
        Generated from the assessment · {fmtDateTime(assessment.generated_at)}
      </p>
    </div>
  );
}

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 } as const;

export function ConditionsPanel({ assessment }: { assessment: AssessmentReport }) {
  const conditions = [...assessment.conditions_of_approval].sort((a, b) => Number(b.blocking) - Number(a.blocking));
  const factors = [...assessment.risk_profile.factors].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  const total = conditions.length + factors.length;

  return (
    <div className={ui.panel}>
      <PanelHeader title="Conditions & risk" aside={total === 0 ? "None" : `${total} item${total === 1 ? "" : "s"}`} />
      {total === 0 ? (
        <p className="px-4 py-3 text-[14px] text-[#2e844a]">No conditions or risk factors flagged.</p>
      ) : (
        <ol>
          {conditions.map((c, i) => (
            <li key={c.id} className="flex gap-3 border-b border-[#e3e6ea] px-4 py-2.5 last:border-b-0">
              <span className={`${mono.className} pt-0.5 text-[12px] text-[#8a909a]`}>{String(i + 1).padStart(2, "0")}</span>
              <div className="min-w-0 flex-1">
                <p className="text-[14px] text-[#1b1e23]">{c.text}</p>
                <p className={`text-[12px] ${ui.muted}`}>{c.reason}</p>
              </div>
              <span className={`shrink-0 text-[12px] ${c.blocking ? "text-[#c23934]" : "text-[#5d6470]"}`}>
                {c.blocking ? "Prior to settlement" : "Advisory"}
              </span>
            </li>
          ))}
          {factors.map((f, i) => (
            <li key={i} className="flex gap-3 border-b border-[#e3e6ea] px-4 py-2.5 last:border-b-0">
              <span
                className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                  f.severity === "high" ? "bg-[#c23934]" : f.severity === "medium" ? "bg-[#c9a227]" : "bg-[#b0b6bf]"
                }`}
              />
              <div className="min-w-0 flex-1">
                <p className="text-[14px] text-[#1b1e23]">{f.label}</p>
                <p className={`text-[12px] ${ui.muted}`}>{f.detail}</p>
              </div>
              <span className="shrink-0 text-[12px] text-[#5d6470]">{humanize(f.severity)} risk</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function ApprovalPanel({
  application,
  assessment,
  chat,
  onDecide,
}: {
  application: LoanApplicationOut | null;
  assessment: AssessmentReport | null;
  chat: ChatReport | null;
  onDecide: () => void;
}) {
  const decided = application && application.status !== "under_review" && application.status !== "submitted";
  const steps: { title: string; detail: string; state: "done" | "current" | "todo" }[] = [
    {
      title: "Credit assessment · AI engine",
      detail: assessment
        ? `Result: ${TIER[assessment.tier]?.label ?? humanize(assessment.tier)} · ${fmtDate(assessment.generated_at)}`
        : "Not run yet",
      state: assessment ? "done" : "todo",
    },
    {
      title: application?.pending_position_title ? `Approver · ${application.pending_position_title}` : "Approver",
      detail: chat?.decision
        ? `${statusLabel(chat.decision.outcome)} · ${fmtDate(chat.decision.decided_at)}`
        : decided
          ? statusLabel(application!.status)
          : "Awaiting decision",
      state: decided || chat?.decision ? "done" : "current",
    },
  ];

  return (
    <div className={ui.panel}>
      <PanelHeader title="Approval" />
      <ol className="space-y-4 px-4 py-3">
        {steps.map((s, i) => (
          <li key={s.title} className="flex gap-3">
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold ${
                s.state === "done"
                  ? "bg-[#2e844a] text-white"
                  : s.state === "current"
                    ? "border-2 border-[#1f5fa8] text-[#1f5fa8]"
                    : "border border-[#cfd3d9] text-[#8a909a]"
              }`}
            >
              {s.state === "done" ? "✓" : i + 1}
            </span>
            <div className="min-w-0">
              <p className="text-[14px] font-medium text-[#1b1e23]">{s.title}</p>
              <p className={`text-[12px] ${s.state === "current" ? "text-[#1f5fa8]" : ui.muted}`}>{s.detail}</p>
            </div>
          </li>
        ))}
      </ol>
      {chat?.decision?.reasoning && (
        <p className="border-t border-[#e3e6ea] px-4 py-3 text-[13px] text-[#343a42]">&ldquo;{chat.decision.reasoning}&rdquo;</p>
      )}
      {application?.status === "under_review" && (
        <div className="border-t border-[#e3e6ea] p-4 print:hidden">
          <button type="button" onClick={onDecide} className={`${ui.brandButton} w-full`}>
            Record decision
          </button>
        </div>
      )}
    </div>
  );
}
