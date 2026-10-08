// Labels and value formatting shared by the application report sections.

export type Tone = "slate" | "indigo" | "emerald" | "amber" | "red";

export function statusLabel(status: string) {
  return status
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export function humanize(value: string): string {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// Australian lender, so Australian formats: "14 May 1990", "$20,000".
const LOCALE = "en-AU";

export function fmtDate(iso: string) {
  // Date-only values ("1990-05-14") are read as local dates, not UTC midnight.
  const date = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return date.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "numeric" });
}

export function fmtDateTime(iso: string) {
  return new Date(iso).toLocaleString(LOCALE, { dateStyle: "medium", timeStyle: "short" });
}

export function fmtMoney(value: number) {
  return value.toLocaleString(LOCALE, { style: "currency", currency: "AUD", maximumFractionDigits: 0 });
}

export function fmtScore(score: number | null | undefined) {
  return score === null || score === undefined ? "—" : score.toFixed(1).replace(/\.0$/, "");
}

export const TIER: Record<string, { label: string; tone: Tone; hint: string }> = {
  auto_eligible: { label: "Meets policy", tone: "emerald", hint: "No policy issues found — ready for your decision" },
  underwriter_review: { label: "Underwriter review", tone: "amber", hint: "Needs a closer look before deciding" },
  conditional: { label: "Conditional", tone: "slate", hint: "Missing data — decision depends on it" },
  decline_recommended: { label: "Decline recommended", tone: "red", hint: "Falls outside lending policy" },
};

export const RISK_TONE: Record<string, Tone> = { low: "emerald", medium: "amber", high: "red" };

export const STATUS_TONE: Record<string, Tone> = {
  draft: "slate",
  submitted: "slate",
  under_review: "amber",
  approved: "emerald",
  rejected: "red",
  disbursed: "indigo",
};

// Assessment metric ids -> the words a credit officer would use.
const METRIC_LABELS: Record<string, string> = {
  nsr: "Net surplus ratio",
  stressed_nsr: "Stressed net surplus ratio",
  dti: "Debt-to-income",
  dsr: "Debt service ratio",
  lvr: "Loan-to-value ratio",
  net_asset_position: "Net asset position",
  contribution_pct: "Deposit contribution",
  genuine_savings: "Genuine savings",
  credit_score: "Credit score",
  worst_rhi_24mo: "Worst repayment history (24 months)",
  worst_rhi_6mo: "Worst repayment history (6 months)",
  missed_payment_count_24mo: "Missed payments (24 months)",
  unpaid_defaults: "Unpaid defaults",
  paid_defaults: "Paid defaults",
  enquiry_velocity_6mo: "Credit enquiries (6 months)",
  bankruptcy_judgment_status: "Bankruptcy or judgments",
  hardship_flags_12mo: "Hardship flags (12 months)",
  employment_stability: "Employment stability",
  industry_sector_risk: "Industry sector risk",
  hem_benchmark: "HEM benchmark",
  age_at_maturity: "Age at loan maturity",
  // Business loans
  dscr: "Debt service coverage ratio (DSCR)",
  icr: "Interest coverage ratio (ICR)",
  ebit: "Earnings before interest and tax (EBIT)",
  ebitda: "EBITDA (cash flow for debt service)",
  total_debt_service: "Total debt service",
  debt_to_equity: "Debt-to-equity (leverage)",
  current_ratio: "Current ratio (liquidity)",
  security_value: "Security value",
  security_coverage_pct: "Security coverage",
  security_type_risk: "Security type risk",
  trading_history_stability: "Trading history",
  tax_compliance: "Tax compliance",
  industry_concentration_status: "Industry concentration",
  turnover_trend_stability: "Turnover trend",
  stressed_dscr: "Stressed DSCR (cash-flow shock)",
  projected_dscr: "Projected DSCR (growth haircut)",
  entity_structure_review: "Entity structure review",
};

export function metricLabel(metric: string) {
  return METRIC_LABELS[metric] ?? humanize(metric);
}

// Formats a metric value using its unit: "AUD" -> money, "score (0-1200)" ->
// "626 / 1200", ratios to two decimals without the word "ratio".
export function fmtMetric(value: unknown, unit: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value !== "number") {
    return typeof value === "object" ? JSON.stringify(value) : humanize(String(value));
  }
  const range = unit?.match(/\((\d+)\s*-\s*(\d+)\)/);
  if (range) return `${value.toLocaleString()} / ${Number(range[2]).toLocaleString()}`;
  if (unit === "AUD") return fmtMoney(value);
  if (unit?.startsWith("AUD/")) return `${fmtMoney(value)} ${unit.slice(4).replace("month", "/ month").replace("year", "/ year")}`;
  if (unit === "%" || unit === "% p.a.") return `${value.toLocaleString()}${unit === "%" ? "%" : "% p.a."}`;
  if (unit === "ratio") return value.toFixed(2);
  if (unit === "count" || !unit) return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  const shown = Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  return `${shown} ${unit}`;
}

// Interview answers, formatted by the slot's schema type.
export function fmtAnswer(value: unknown, type: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (type === "currency" && typeof value === "number") return fmtMoney(value);
  if (type === "date" && typeof value === "string") return fmtDate(value);
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "object") return JSON.stringify(value);
  return type === "choice" ? humanize(String(value)) : String(value);
}

export const ANSWER_GROUPS: { id: string; label: string }[] = [
  { id: "identity", label: "Identity" },
  { id: "household", label: "Household" },
  { id: "employment", label: "Employment" },
  { id: "income", label: "Income" },
  { id: "expenses", label: "Living expenses" },
  { id: "liabilities", label: "Liabilities" },
  { id: "assets", label: "Assets" },
  { id: "loan", label: "Loan" },
  { id: "purpose", label: "Purpose" },
  { id: "business", label: "Business" },
  { id: "business_financials", label: "Business financials" },
  { id: "security", label: "Security" },
  { id: "consent", label: "Consent" },
  { id: "confirmation", label: "Confirmation" },
];
