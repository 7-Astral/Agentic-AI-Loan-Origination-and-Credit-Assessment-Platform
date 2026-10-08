// Business-loan report sections — replaces the retail "Five C's" framing with
// the four themes a commercial credit analyst actually works through:
// financial ratios, serviceability vs. projections, entity/industry risk, and
// the annual review covenant. Everything here reads off data the API already
// returns (chat.assessment.metrics, chat.slots, assessment.conditions_of_approval) —
// no bespoke backend endpoint for this view.
import type { AssessmentReport, ChatReport } from "@/lib/api";
import { CashFlowWaterfall } from "./ReportCharts";
import { FieldGrid, PanelHeader, Pill, Section, ui } from "./ReportSections";
import { fmtMoney, humanize, type Tone } from "./format";

type MetricEntry = { state: string; value: unknown; unit: string | null };
type MetricsMap = Record<string, MetricEntry>;

function metric(metrics: MetricsMap | undefined, key: string): MetricEntry | null {
  const m = metrics?.[key];
  return m && m.state === "computed" ? m : null;
}

function metricNumber(metrics: MetricsMap | undefined, key: string): number | null {
  const v = metric(metrics, key)?.value;
  return typeof v === "number" ? v : null;
}

function slotValue(chat: ChatReport, key: string): unknown {
  return chat.slots.find((s) => s.slot_key === key)?.value ?? null;
}

function slotNumber(chat: ChatReport, key: string): number | null {
  const v = slotValue(chat, key);
  return typeof v === "number" ? v : null;
}

function ratioStatus(
  rules: { rule_id: string }[],
  failId: string,
  flagId?: string,
): { tone: Tone; label: string } {
  const fired = new Set(rules.map((r) => r.rule_id));
  if (fired.has(failId)) return { tone: "red", label: "Fail" };
  if (flagId && fired.has(flagId)) return { tone: "amber", label: "Flag" };
  return { tone: "emerald", label: "Pass" };
}

function fmtRatio(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(2)}x`;
}

export function FinancialRatiosSection({ chat }: { chat: ChatReport }) {
  const metrics = chat.assessment?.metrics;
  const rules = chat.assessment?.rule_results ?? [];

  const cards: {
    key: string;
    title: string;
    sub: string;
    value: number | null;
    target: string;
    status: { tone: Tone; label: string };
  }[] = [
    {
      key: "dscr",
      title: "Debt service coverage ratio",
      sub: "Operating cash flow ÷ principal + interest due",
      value: metricNumber(metrics, "dscr"),
      target: "Target ≥ 1.25x–1.50x",
      status: ratioStatus(rules, "biz_dscr_fail", "biz_dscr_flag"),
    },
    {
      key: "icr",
      title: "Interest coverage ratio",
      sub: "EBIT ÷ interest expense",
      value: metricNumber(metrics, "icr"),
      target: "Target ≥ 2.0x",
      status: ratioStatus(rules, "biz_icr_fail", "biz_icr_flag"),
    },
    {
      key: "debt_to_equity",
      title: "Leverage (debt-to-equity)",
      sub: "Total liabilities ÷ equity",
      value: metricNumber(metrics, "debt_to_equity"),
      target: "Lower is stronger",
      status: ratioStatus(rules, "biz_leverage_high", "biz_leverage_flag"),
    },
    {
      key: "current_ratio",
      title: "Current ratio (liquidity)",
      sub: "Current assets ÷ current liabilities",
      value: metricNumber(metrics, "current_ratio"),
      target: "Target ≥ 1.0x",
      status: ratioStatus(rules, "biz_liquidity_fail", "biz_liquidity_flag"),
    },
  ];

  const netProfit = slotNumber(chat, "net_profit_before_tax");
  const interest = slotNumber(chat, "interest_expense_annual");
  const depreciation = slotNumber(chat, "depreciation_amortisation_annual");
  const ebit = metricNumber(metrics, "ebit");
  const ebitda = metricNumber(metrics, "ebitda");

  return (
    <div className={ui.panel}>
      <PanelHeader title="1. Financial statement analysis" aside="DSCR, ICR, leverage & liquidity" />
      <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
        {cards.map((c) => (
          <div key={c.key} className="border border-[#e3e6ea] p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[13px] font-medium text-[#1b1e23]">{c.title}</p>
              <Pill tone={c.value === null ? "slate" : c.status.tone}>{c.value === null ? "No data" : c.status.label}</Pill>
            </div>
            <p className="mt-1 text-[22px] font-semibold tabular-nums text-[#1b1e23]">{fmtRatio(c.value)}</p>
            <p className={`text-[12px] ${ui.muted}`}>
              {c.sub} · {c.target}
            </p>
          </div>
        ))}
      </div>
      <Section title="Spread-tendering — how EBIT/EBITDA were built" defaultOpen={false}>
        <FieldGrid
          fields={[
            { label: "Net profit before tax", value: netProfit !== null ? fmtMoney(netProfit) : "—" },
            { label: "+ Interest expense (add-back)", value: interest !== null ? fmtMoney(interest) : "—" },
            { label: "= EBIT", value: ebit !== null ? fmtMoney(ebit) : "—" },
            { label: "+ Depreciation & amortisation (add-back)", value: depreciation !== null ? fmtMoney(depreciation) : "—" },
            { label: "= EBITDA", value: ebitda !== null ? fmtMoney(ebitda) : "—" },
          ]}
        />
      </Section>
    </div>
  );
}

export function ServiceabilityProjectionsSection({ chat }: { chat: ChatReport }) {
  const metrics = chat.assessment?.metrics;

  const netProfit = slotNumber(chat, "net_profit_before_tax");
  const interest = slotNumber(chat, "interest_expense_annual");
  const depreciation = slotNumber(chat, "depreciation_amortisation_annual");
  const ebit = metricNumber(metrics, "ebit");
  const ebitda = metricNumber(metrics, "ebitda");

  const baseDscr = metricNumber(metrics, "dscr");
  const stressedDscr = metricNumber(metrics, "stressed_dscr");
  const projected = metric(metrics, "projected_dscr");
  const projectedRaw = metrics?.projected_dscr;
  const growthPct = slotNumber(chat, "projected_revenue_growth_pct");

  const turnoverYears = [
    { label: "2 years prior", value: slotNumber(chat, "two_years_prior_annual_turnover") },
    { label: "Prior year", value: slotNumber(chat, "prior_year_annual_turnover") },
    { label: "Most recent year", value: slotNumber(chat, "annual_turnover") },
  ].filter((y) => y.value !== null) as { label: string; value: number }[];
  const trend = metric(metrics, "turnover_trend_stability");

  return (
    <div className={ui.panel}>
      <PanelHeader title="2. Serviceability vs. projections" aside="Historical cash flow & stress-tested forecasts" />
      <div className="p-4">
        <CashFlowWaterfall netProfit={netProfit} interestExpense={interest} ebit={ebit} depreciation={depreciation} ebitda={ebitda} />
      </div>
      <Section title="Stress testing">
        <FieldGrid
          fields={[
            { label: "Base DSCR", value: fmtRatio(baseDscr) },
            { label: "Stressed DSCR (cash-flow shock)", value: fmtRatio(stressedDscr) },
            ...(projectedRaw && projectedRaw.state !== "not_applicable"
              ? [
                  {
                    label: growthPct !== null ? `Projected DSCR (${growthPct}% growth, haircut applied)` : "Projected DSCR",
                    value: fmtRatio(projected ? (projected.value as number) : null),
                  },
                ]
              : []),
          ]}
        />
        <p className={`px-0 pt-2 text-[12px] ${ui.muted}`}>
          Stressed DSCR applies a standard cash-flow shock to every business facility. Projected DSCR only applies to
          expansion-purpose loans — it stress-tests management&apos;s revenue growth assumption with a haircut before
          relying on it.
        </p>
      </Section>
      {turnoverYears.length >= 2 && (
        <Section title="Turnover trend">
          <FieldGrid fields={turnoverYears.map((y) => ({ label: y.label, value: fmtMoney(y.value) }))} />
          {trend && (
            <p className="mt-2">
              <Pill tone={trend.value === "stable" ? "emerald" : "amber"}>{humanize(String(trend.value))}</Pill>
            </p>
          )}
        </Section>
      )}
    </div>
  );
}

const CONCENTRATION_EXPLAIN: Record<string, string> = {
  open: "No concentration limit currently applies to this sector.",
  watchlist: "The bank is monitoring exposure to this sector — new lending needs extra confirmation.",
  restricted: "The bank's internal policy currently restricts new lending in this sector.",
};

export function EntityIndustryRiskSection({ chat }: { chat: ChatReport }) {
  const metrics = chat.assessment?.metrics;

  const entityStructure = slotValue(chat, "entity_structure");
  const applicantRole = slotValue(chat, "applicant_role");
  const entityDocs = slotValue(chat, "entity_documents_note");
  const structureReview = metric(metrics, "entity_structure_review");

  const industry = slotValue(chat, "industry");
  const industryRisk = metric(metrics, "industry_sector_risk");
  const concentration = metric(metrics, "industry_concentration_status");

  return (
    <div className={ui.panel}>
      <PanelHeader title="3. Entity & industry risk" aside="Structure review and sector concentration" />
      <Section title="Entity structure review">
        <FieldGrid
          fields={[
            { label: "Entity structure", value: entityStructure ? humanize(String(entityStructure)) : "—" },
            { label: "Applicant's role", value: applicantRole ? humanize(String(applicantRole)) : "—" },
            { label: "Constituent documents", value: entityDocs ? String(entityDocs) : "Not provided" },
          ]}
        />
        {structureReview && (
          <p className="mt-2 flex items-center gap-2">
            <Pill tone={structureReview.value === "needs_review" ? "amber" : "emerald"}>
              {structureReview.value === "needs_review" ? "Needs review" : "Reviewed"}
            </Pill>
            {structureReview.value === "needs_review" && (
              <span className={`text-[12px] ${ui.muted}`}>
                Partnership/company/trust constituent documents haven&apos;t been provided yet — ultimate beneficial
                owners, corporate trustee and guarantee arrangements still need manual sign-off.
              </span>
            )}
          </p>
        )}
      </Section>
      <Section title="Industry SWOT & concentration">
        <FieldGrid
          fields={[
            { label: "Industry", value: industry ? humanize(String(industry)) : "—" },
            {
              label: "Industry sector risk",
              value: industryRisk ? (
                <Pill tone={industryRisk.value === "high" ? "red" : industryRisk.value === "medium" ? "amber" : "emerald"}>
                  {humanize(String(industryRisk.value))}
                </Pill>
              ) : (
                "—"
              ),
            },
          ]}
        />
        {concentration && (
          <p className="mt-3 flex flex-wrap items-center gap-2 text-[13px] text-[#343a42]">
            <Pill tone={concentration.value === "restricted" ? "red" : concentration.value === "watchlist" ? "amber" : "emerald"}>
              {humanize(String(concentration.value))}
            </Pill>
            <span>{CONCENTRATION_EXPLAIN[String(concentration.value)] ?? ""}</span>
          </p>
        )}
      </Section>
    </div>
  );
}

export function AnnualReviewSection({ assessment }: { assessment: AssessmentReport }) {
  const condition = assessment.conditions_of_approval.find((c) => c.id === "annual_review");
  return (
    <div className={`${ui.panel} border-l-4 border-l-[#1f5fa8]`}>
      <PanelHeader title="4. Annual review policy" aside="Actively managed, not set-and-forget" />
      <div className="px-4 py-3">
        {condition ? (
          <>
            <p className="text-[14px] leading-6 text-[#1b1e23]">{condition.text}</p>
            <p className={`mt-1 text-[12px] ${ui.muted}`}>{condition.reason}</p>
          </>
        ) : (
          <p className={`text-[13px] ${ui.muted}`}>No standing annual-review condition recorded for this facility.</p>
        )}
      </div>
    </div>
  );
}
