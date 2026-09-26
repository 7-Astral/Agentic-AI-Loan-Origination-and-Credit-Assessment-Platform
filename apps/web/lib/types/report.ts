export type ScoredMetric = {
  metric: string;
  raw_value: unknown;
  unit: string | null;
  channel: string | null;
  normalized_score: number;
};

export type SkippedMetric = {
  metric: string;
  reason: string;
};

export type GroupScoreState = "computed" | "unavailable" | "not_applicable";

export type GroupScore = {
  score: number | null;
  state: GroupScoreState;
  metrics_used: ScoredMetric[];
  metrics_skipped: SkippedMetric[];
};

export type ConditionOfApproval = {
  id: string;
  category: string;
  text: string;
  reason: string;
  blocking: boolean;
};

export type RuleResult = {
  rule_id: string;
  status: string;
  message?: string | null;
  missing?: string[] | null;
  detail?: string | null;
  inputs?: Record<string, unknown> | null;
};

export type RuleBasedIndicator = {
  tier: string;
  fail_count: number;
  flag_count: number;
  provisional_count: number;
};

export type FiveC = "capacity" | "capital" | "character" | "collateral" | "conditions";

export type DecisionTier = "auto_eligible" | "underwriter_review" | "decline_recommended";

export type ApplicantFact = {
  id: string;
  label: string;
  value: unknown;
};

export type KeyFigure = {
  metric: string;
  label: string;
  value: unknown;
  unit: string | null;
};

export type PolicyComparison = {
  metric: string;
  label: string;
  value: unknown;
  unit: string | null;
  threshold: unknown;
  threshold_label: string;
  meets_threshold: boolean;
};

export type DocumentSummary = {
  document_id: string;
  verification_type: string;
  original_filename: string;
  status: string;
  uploaded_at: string;
  extracted: boolean;
};

export type Verification = {
  slot_id: string;
  declared_value: string;
  extracted_value: string;
  status: string;
  checked_at: string;
};

export type TranscriptMessage = {
  role: string;
  content: string;
  turn: number | null;
  created_at: string;
};

export type RiskFactor = {
  severity: "high" | "medium" | "low";
  label: string;
  detail: string;
};

export type RiskProfile = {
  category: "high" | "medium" | "low";
  factors: RiskFactor[];
};

export type ApplicationReport = {
  session_id: string;
  bank_id: string;
  product_code: string;
  product_name: string | null;
  status: string;
  generated_at: string;
  group_scores: Partial<Record<FiveC, GroupScore>>;
  overall_score: number | null;
  weights_applied: Partial<Record<FiveC, number>>;
  score_bands_applied: Record<string, number>;
  tier: DecisionTier;
  data_completeness: Partial<Record<FiveC, string>>;
  conditions_of_approval: ConditionOfApproval[];
  rule_results: RuleResult[];
  rule_based_indicator: RuleBasedIndicator;
  metrics_computed: number;
  metrics_total: number;
  narrative_summary: string;
  risk_profile: RiskProfile;
  applicant_summary: ApplicantFact[];
  key_figures: KeyFigure[];
  policy_comparison: PolicyComparison[];
  documents: DocumentSummary[];
  verifications: Verification[];
  transcript: TranscriptMessage[];
};

export type ApplicationSummary = {
  session_id: string;
  product_code: string | null;
  status: string;
  overall_score: number | null;
  tier: string | null;
  created_at: string;
};

export type ApplicationList = {
  applications: ApplicationSummary[];
  total: number;
};
