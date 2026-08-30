const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function startApplication(productCode?: string) {
  return request<TurnResponse>("/api/v1/applications", {
    method: "POST",
    body: JSON.stringify(productCode ? { product_code: productCode } : {}),
  });
}

export function sendMessage(sessionId: string, message: string) {
  return request<TurnResponse>(`/api/v1/applications/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}