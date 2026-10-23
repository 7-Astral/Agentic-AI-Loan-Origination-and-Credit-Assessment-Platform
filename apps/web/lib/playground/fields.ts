import type { PlaygroundProduct } from "@/lib/types/playground";

export type FieldKind = "currency" | "number" | "text" | "date" | "select" | "toggle";

export type Field = {
  key: string;
  label: string;
  kind: FieldKind;
  hint?: string;
  options?: { value: string; label: string }[];
};

export type Section = {
  id: string;
  title: string;
  fields: Field[];
  /** Hide the whole section for products it does not apply to. */
  appliesTo?: (product: PlaygroundProduct | undefined) => boolean;
};

const opts = (...values: string[]) => values.map((value) => ({ value, label: prettify(value) }));

const ACRONYMS = new Set(["nsr", "dti", "dsr", "lmi", "rhi", "lvr", "hem", "hecs", "help", "bnpl", "vin"]);

export function prettify(name: string): string {
  const words = name.split("_").map((word) => (ACRONYMS.has(word) ? word.toUpperCase() : word));
  const spaced = words.join(" ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

const isHome = (p?: PlaygroundProduct) => p?.loan_type === "home";
const isVehicle = (p?: PlaygroundProduct) => p?.category === "vehicle";

export const SECTIONS: Section[] = [
  {
    id: "loan",
    title: "Loan requested",
    fields: [
      { key: "loan_amount", label: "Loan amount", kind: "currency" },
      { key: "loan_term_months", label: "Term (months)", kind: "number" },
      {
        key: "loan_purpose",
        label: "Purpose",
        kind: "select",
        options: opts(
          "purchase_property", "purchase_vehicle", "debt_consolidation", "home_improvement",
          "business_use", "travel", "medical", "education", "other",
        ),
      },
    ],
  },
  {
    id: "applicant",
    title: "Applicant",
    fields: [
      { key: "full_name", label: "Full name", kind: "text" },
      { key: "date_of_birth", label: "Date of birth", kind: "date" },
      {
        key: "marital_status",
        label: "Marital status",
        kind: "select",
        options: opts("single", "married", "de_facto", "separated"),
      },
      { key: "dependants", label: "Dependants", kind: "number" },
      {
        key: "credit_check_consent",
        label: "Consented to credit check",
        kind: "toggle",
        hint: "Without consent the bureau is never contacted",
      },
    ],
  },
  {
    id: "employment",
    title: "Employment and residency",
    fields: [
      {
        key: "employment_status",
        label: "Employment",
        kind: "select",
        options: opts("full_time", "part_time", "casual", "self_employed", "retired", "unemployed", "student"),
      },
      { key: "employer_name", label: "Employer", kind: "text" },
      {
        key: "employer_industry",
        label: "Industry",
        kind: "select",
        options: opts(
          "agriculture_forestry_fishing", "mining", "manufacturing", "utilities", "construction", "wholesale_trade",
          "retail_trade", "accommodation_food", "transport_postal_warehousing", "information_media_telecom",
          "finance_insurance", "property_rental", "professional_scientific_technical", "administrative_support",
          "public_administration_safety", "education_training", "health_care_social_assistance", "arts_recreation",
          "other_services",
        ),
      },
      { key: "months_in_current_role", label: "Months in current role", kind: "number" },
      { key: "on_probation", label: "Currently on probation", kind: "toggle" },
      { key: "abn_years_trading", label: "Years trading (self-employed)", kind: "number" },
      {
        key: "residency_status",
        label: "Residency",
        kind: "select",
        options: opts("citizen", "permanent_resident", "temporary_visa"),
      },
      { key: "visa_expiry_date", label: "Visa expiry date", kind: "date" },
    ],
  },
  {
    id: "income",
    title: "Income",
    fields: [
      { key: "gross_annual_income", label: "Gross annual income", kind: "currency" },
      { key: "net_income_amount", label: "Take-home pay", kind: "currency" },
      {
        key: "net_income_frequency",
        label: "Pay frequency",
        kind: "select",
        options: opts("weekly", "fortnightly", "monthly"),
      },
    ],
  },
  {
    id: "expenses",
    title: "Living expenses (per month)",
    fields: [
      { key: "exp_food_groceries", label: "Food and groceries", kind: "currency" },
      { key: "exp_rent_board", label: "Rent or board", kind: "currency" },
      { key: "exp_insurance", label: "Insurance", kind: "currency" },
      { key: "exp_clothing_personal_care", label: "Clothing and personal care", kind: "currency" },
      { key: "exp_recreation_holidays", label: "Recreation and holidays", kind: "currency" },
      { key: "exp_education_childcare", label: "Education and childcare", kind: "currency" },
      { key: "exp_medical_health", label: "Medical and health", kind: "currency" },
      { key: "exp_other_housing", label: "Other housing costs", kind: "currency" },
      { key: "exp_phone_internet_media", label: "Phone, internet and media", kind: "currency" },
      { key: "exp_vehicle_transport", label: "Vehicle and transport", kind: "currency" },
    ],
  },
  {
    id: "position",
    title: "Assets and liabilities",
    fields: [
      { key: "savings_balance", label: "Savings", kind: "currency" },
      { key: "property_equity_value", label: "Property owned (value)", kind: "currency" },
      { key: "vehicles_value", label: "Vehicles", kind: "currency" },
      { key: "investments_value", label: "Shares and funds", kind: "currency" },
      { key: "mortgage_balance", label: "Mortgage balance", kind: "currency" },
      { key: "mortgage_repayment_monthly", label: "Mortgage repayment (monthly)", kind: "currency" },
      { key: "other_loan_repayments_monthly", label: "Other loan repayments (monthly)", kind: "currency" },
      { key: "credit_card_limit_total", label: "Credit card limits", kind: "currency" },
      { key: "credit_card_balance_total", label: "Credit card balances", kind: "currency" },
      { key: "hecs_help_balance", label: "HECS/HELP balance", kind: "currency" },
    ],
  },
  {
    id: "home_deposit",
    title: "Property and deposit",
    appliesTo: isHome,
    fields: [
      { key: "property_price", label: "Property price", kind: "currency" },
      { key: "deposit_amount", label: "Deposit", kind: "currency" },
      {
        key: "deposit_source",
        label: "Deposit source",
        kind: "select",
        options: opts("genuine_savings", "gift", "inheritance", "sale_of_asset", "equity_release", "other"),
      },
      {
        key: "repayment_type",
        label: "Repayment type",
        kind: "select",
        options: opts("principal_and_interest", "interest_only"),
      },
      { key: "has_guarantor", label: "Guarantor involved", kind: "toggle" },
    ],
  },
  {
    id: "vehicle_deposit",
    title: "Vehicle and deposit",
    appliesTo: isVehicle,
    fields: [
      { key: "vehicle_purchase_price", label: "Purchase price", kind: "currency" },
      { key: "trade_in_or_deposit", label: "Trade-in or deposit", kind: "currency" },
      { key: "vehicle_year", label: "Year of manufacture", kind: "number" },
      { key: "wants_balloon", label: "Wants a balloon payment", kind: "toggle" },
      { key: "balloon_percentage", label: "Balloon (% of price)", kind: "number" },
    ],
  },
];

/** Plain-English names for the metrics; anything missing falls back to prettify(). */
export const METRIC_LABELS: Record<string, string> = {
  gross_annual_income: "Gross annual income",
  shaded_income: "Assessed income (after shading)",
  net_monthly_income: "Declared take-home pay (monthly)",
  assessed_net_income: "Assessed take-home pay (after shading)",
  net_to_gross_ratio: "Take-home as a share of gross",
  declared_expenses: "Declared expenses",
  verified_expenses: "Expenses seen in bank statement",
  hem_benchmark: "HEM expense benchmark",
  assessed_living_expenses: "Assessed living expenses",
  existing_commitments: "Existing commitments",
  assessment_rate: "Assessment interest rate",
  proposed_repayment: "Proposed monthly repayment",
  monthly_surplus: "Monthly surplus",
  nsr: "Net surplus ratio (NSR)",
  dti: "Debt-to-income (DTI)",
  dsr: "Debt service ratio (DSR)",
  deposit_amount: "Deposit",
  contribution_pct: "Contribution to purchase",
  required_contribution_pct: "Minimum contribution required",
  genuine_savings: "Genuine savings (from statement)",
  net_asset_position: "Net asset position",
  credit_score: "Credit score",
  worst_rhi_6mo: "Worst arrears, last 6 months",
  worst_rhi_24mo: "Worst arrears, last 24 months",
  missed_payment_count_24mo: "Missed payments, last 24 months",
  unpaid_defaults: "Unpaid defaults",
  paid_defaults: "Paid defaults",
  enquiry_velocity_6mo: "Credit enquiries, last 6 months",
  bankruptcy_judgment_status: "Bankruptcy or judgment",
  hardship_flags_12mo: "Hardship arrangements, last 12 months",
  undisclosed_liabilities: "Undisclosed liabilities (monthly)",
  security_value: "Security value",
  lvr: "Loan-to-value ratio (LVR)",
  valuation_status: "Valuation status",
  property_type_risk: "Property type risk",
  postcode_risk: "Postcode risk",
  loan_purpose: "Loan purpose",
  loan_amount_and_term: "Loan amount and term",
  product_structure: "Product structure",
  industry_sector_risk: "Industry risk",
  purpose_eligibility: "Purpose eligibility",
  product_limit_breaches: "Outside product limits",
  repayment_structure: "Repayment structure",
  balloon_pct: "Balloon payment",
  max_balloon_pct: "Maximum balloon allowed",
  vehicle_age_assessed: "Vehicle age (as assessed)",
  vehicle_age_limit: "Vehicle age limit",
  age_at_maturity: "Age when the loan ends",
  max_age_at_maturity: "Maximum age when the loan ends",
  visa_shortfall_months: "Visa shortfall against the term",
  stressed_nsr: "NSR if income falls",
  employment_stability: "Employment stability",
};

export const GROUP_LABELS: Record<string, { title: string; blurb: string }> = {
  capacity: { title: "Capacity", blurb: "Can they afford the repayments?" },
  capital: { title: "Capital", blurb: "What do they put in and own?" },
  character: { title: "Character", blurb: "How have they handled credit before?" },
  collateral: { title: "Collateral", blurb: "What secures the loan?" },
  conditions: { title: "Conditions", blurb: "What is the loan for and on what terms?" },
};
