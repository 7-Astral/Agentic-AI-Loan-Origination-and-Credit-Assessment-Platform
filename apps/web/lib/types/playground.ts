export type FilledValue = string | number | boolean;
export type Filled = Record<string, FilledValue>;

export type Preset = {
  id: string;
  label: string;
  description: string;
  product_code: string;
  bureau_scenario: string;
  use_sample_statement: boolean;
  filled: Filled;
};

export type PlaygroundProduct = {
  product_code: string;
  name: string;
  loan_type: string;
  category: string;
  secured: boolean;
  interest_rate: number;
  min_amount: number;
  max_amount: number;
  min_term_months: number;
  max_term_months: number;
  max_lvr: number | null;
};

export type BureauScenario = { name: string; description: string; weight: number };

export type PlaygroundOptions = {
  presets: Preset[];
  products: PlaygroundProduct[];
  bureau_scenarios: BureauScenario[];
};

export type AssessRequest = {
  product_code: string;
  filled: Filled;
  bureau_scenario: string | null;
  use_sample_statement: boolean;
  policy_overrides?: Record<string, Record<string, number>>;
};

export type RouteTier = "auto_eligible" | "underwriter_review" | "conditional" | "decline_recommended";

export type RouteResult = {
  tier: RouteTier;
  fail_count: number;
  flag_count: number;
  provisional_count: number;
};

export type MetricState = "computed" | "unavailable" | "not_applicable" | "stale";

export type MetricResult = {
  state: MetricState;
  value: number | string | Record<string, unknown> | null;
  unit: string | null;
  channel: string;
  inputs: Record<string, unknown> | null;
};

export type RuleResult = {
  rule_id: string;
  status: "fail" | "flag" | "provisional" | "pass" | "error";
  message?: string;
  missing?: string[];
  inputs?: Record<string, number | string>;
  detail?: string;
};

export const GROUP_ORDER = ["capacity", "capital", "character", "collateral", "conditions"] as const;
export type GroupName = (typeof GROUP_ORDER)[number];

export type BureauSummary =
  | { status: "pulled"; scenario: string; report_id: string }
  | { status: "skipped"; reason: string };

export type ApprovalCondition = {
  id: string;
  category: GroupName;
  text: string;
  reason: string;
  blocking: boolean;
};

export type AssessResponse = {
  product: PlaygroundProduct;
  route: RouteResult;
  rule_results: RuleResult[];
  conditions_of_approval?: ApprovalCondition[];
  groups: Record<GroupName, Record<string, MetricResult>>;
  metrics_computed: number;
  metrics_total: number;
  bureau: BureauSummary;
};
