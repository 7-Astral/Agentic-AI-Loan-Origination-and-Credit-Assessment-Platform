export type SlotHint = {
  id: string;
  label: string;
  type: string;
  options?: string[] | null;
};

export type Progress = {
  answered: number;
  remaining_known: number;
  current_phase: number | null;
  complete: boolean;
};

export type TurnResponse = {
  session_id: string;
  stage: string;
  question: string | null;
  slots_in_play: SlotHint[];
  progress: Progress | null;
  complete: boolean;
  escalated: boolean;
  product_code: string | null;
};

export type TranscriptMessage = {
  role: "assistant" | "user";
  content: string;
};

export type ApplicationState = {
  session_id: string;
  product_code: string;
  schema_version: string;
  progress: Progress;
  filled: Record<string, unknown>;
  provenance: Record<string, unknown>;
  transcript: TranscriptMessage[];
};

export type RequiredDocument = {
  code: string;
  name: string;
  status: "not_uploaded" | "uploaded" | "extracted" | "needs_reupload";
  document_id: string | null;
};