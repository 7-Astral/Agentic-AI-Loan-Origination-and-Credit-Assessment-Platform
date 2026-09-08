export type FiveCKey = "character" | "capacity" | "capital" | "collateral" | "conditions";

export type FiveCSource =
  "bureau-verified" | "abn-verified" | "applicant-declared" | "calculated" | "unavailable";

export type FiveCConfidence = "high" | "medium" | "low";

export type FieldRequirement = "required" | "confidence";

export interface FiveCField {
  value: unknown;
  source: FiveCSource;
  confidence: FiveCConfidence;
  notes: string | null;
}

export interface FiveCs {
  character: FiveCField;
  capacity: FiveCField;
  capital: FiveCField;
  collateral: FiveCField;
  conditions: FiveCField;
}

export interface MissingField {
  field: string;
  label: string;
  five_c: FiveCKey;
  requirement: FieldRequirement;
}

export interface CompletenessInfo {
  score: number;
  missing_fields: MissingField[];
}

export interface DataSourceEntry {
  source: string;
  called: boolean;
  matched: boolean | null;
  reason: string | null;
}

export interface RiskAssessmentReport {
  application_id: string;
  assessed_at: string;
  completeness: CompletenessInfo;
  five_cs: FiveCs;
  data_sources: DataSourceEntry[];
}
