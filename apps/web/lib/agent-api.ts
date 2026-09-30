// Client for the chat-agent backend (agent-backend), a separate service from
// the main platform API (see lib/api.ts). It speaks its own REST contract —
// discovery/interview turns, document upload, assessment, and a final
// "submit" call that hands the completed interview into the main platform's
// real loan pipeline (see services/api's /api/v1/applications endpoint).
import { handleExpiredSession } from "./session";

const AGENT_API_URL = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8001";

export interface SlotHint {
  id: string;
  label: string;
  type: string;
  options: string[] | null;
}

export interface Progress {
  answered: number;
  remaining_known: number;
  current_phase: number | null;
  complete: boolean;
}

export interface ProductOption {
  product_code: string;
  name: string;
  interest_rate: number | null;
  comparison_rate: number | null;
  rate_type: string | null;
  min_amount: number;
  max_amount: number;
  min_term_months: number;
  max_term_months: number;
  features: string[];
}

export interface TurnResponse {
  session_id: string;
  stage: string;
  question: string | null;
  slots_in_play: SlotHint[];
  progress: Progress | null;
  complete: boolean;
  escalated: boolean;
  product_code: string | null;
  products?: ProductOption[] | null;
}

export interface RequiredDocument {
  code: string;
  name: string;
  status: string;
  document_id: string | null;
  verification: "match" | "mismatch" | null;
}

export interface UploadDocumentResult {
  document_id: string;
  verification_type: string;
  status: string;
  uploaded_at: string;
  reason?: string;
}

export interface AssessmentMetric {
  state: string;
  value: unknown;
  unit: string | null;
}

export interface AssessmentResult {
  session_id: string;
  product_code: string;
  metrics: Record<string, AssessmentMetric>;
  metrics_computed: number;
  metrics_total: number;
  rule_results: Array<{ rule_id: string; status: string; message?: string }>;
  route: { outcome?: string; [key: string]: unknown };
}

export interface SubmitResult {
  application_id: string;
  status: string;
  outcome: "auto_approved" | "escalated" | string;
  pending_position_title: string | null;
}

export class AgentApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${AGENT_API_URL}${path}`, { ...options, headers, cache: "no-store" });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse errors */
    }
    // Same JWT, same "Invalid or expired token" as services/api — see
    // agent-backend's app/core/identity.get_customer_id_from_token.
    if (res.status === 401 && token) handleExpiredSession();
    throw new AgentApiError(res.status, typeof detail === "string" ? detail : res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const agentApi = {
  start: (token: string | null, bankId?: string) =>
    request<TurnResponse>("/api/v1/applications", { method: "POST", body: JSON.stringify({ bank_id: bankId }) }, token),

  sendMessage: (token: string | null, sessionId: string, message: string) =>
    request<TurnResponse>(
      `/api/v1/applications/${sessionId}/messages`,
      { method: "POST", body: JSON.stringify({ message }) },
      token
    ),

  requiredDocuments: (token: string | null, sessionId: string) =>
    request<{ session_id: string; documents: RequiredDocument[] }>(
      `/api/v1/applications/${sessionId}/documents/required`,
      {},
      token
    ),

  uploadDocument: (token: string | null, sessionId: string, verificationType: string, file: File) => {
    const form = new FormData();
    form.append("verification_type", verificationType);
    form.append("file", file);
    return request<UploadDocumentResult>(
      `/api/v1/applications/${sessionId}/documents`,
      { method: "POST", body: form },
      token
    );
  },

  // WhatsApp-style single attach button: no verification_type needed, the
  // backend auto-picks the next not-yet-uploaded required document.
  uploadNextDocument: (token: string | null, sessionId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadDocumentResult>(
      `/api/v1/applications/${sessionId}/documents/next`,
      { method: "POST", body: form },
      token
    );
  },

  assessment: (token: string | null, sessionId: string) =>
    request<AssessmentResult>(`/api/v1/applications/${sessionId}/assessment`, {}, token),

  submit: (token: string | null, sessionId: string) =>
    request<SubmitResult>(`/api/v1/applications/${sessionId}/submit`, { method: "POST" }, token),
};
