export type DocumentField = { id: string; type: string };

export type DocumentCheck = {
  slot_id: string;
  label: string;
  extracted_field: string;
  compare: "exact" | "fuzzy_text" | "currency_tolerance";
  tolerance_pct: number | null;
};

export type DocumentTypeInfo = {
  code: string;
  name: string;
  fields: DocumentField[];
  checks: DocumentCheck[];
};

export type Recording = { model: string; recorded_at: string };

export type Box = { x: number; y: number; w: number; h: number };

export type SampleLayout = { width: number; height: number; fields: Record<string, Box>; rows: Box[] };

export type DocumentSample = {
  id: string;
  label: string;
  description: string;
  verification_type: string;
  declared: Record<string, string>;
  mismatch_example: Record<string, string>;
  layout: SampleLayout | null;
  recording: Recording | null;
};

export type DocumentOptions = {
  samples: DocumentSample[];
  document_types: DocumentTypeInfo[];
};

export type ExtractedField = { id: string; type: string; value: string | number | null };

export type ExtractedTransaction = {
  date: string;
  description: string;
  amount: number;
  direction: "credit" | "debit";
  category: string | null;
};

export type PageBox = Box & { page: number };

export type PdfPage = { image: string; width: number; height: number };

export type PdfLayout = { fields: Record<string, PageBox>; rows: PageBox[] };

export type BalanceCheck = {
  opening_balance: number;
  closing_balance: number;
  total_in: number;
  total_out: number;
  rows: number;
  reconciled: boolean;
};

export type Verification = {
  slot_id: string;
  declared_value: string;
  extracted_value: string;
  status: "match" | "mismatch" | "missing" | "on_file";
  compare: DocumentCheck["compare"] | null;
  tolerance_pct: number | null;
};

export type ImpactMetric = {
  state: string;
  value: number | null;
  unit: string | null;
  inputs: Record<string, number> | null;
};

export type ExtractResponse = {
  source: "live" | "recorded";
  method: "pdf_text" | "ai_vision";
  checks: BalanceCheck | null;
  warnings: string[];
  pdf_pages: PdfPage[] | null;
  pdf_layout: PdfLayout | null;
  recording: Recording | null;
  duration_ms: number;
  matches_claimed_type: boolean;
  notes: string;
  fields: ExtractedField[];
  transactions: ExtractedTransaction[] | null;
  verifications: Verification[];
  assessment_impact: {
    verified_expenses: ImpactMetric;
    genuine_savings: ImpactMetric;
    statement_days: number | null;
  } | null;
};

export type ExtractRequest = {
  verificationType: string;
  declared: Record<string, string>;
  sampleId: string | null;
  live: boolean;
  file: File | null;
  categorize?: boolean;
};
