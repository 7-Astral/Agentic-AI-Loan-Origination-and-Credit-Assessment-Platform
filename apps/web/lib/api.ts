import type { ApplicationState, RequiredDocument, TurnResponse } from "@/lib/types/application.ts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export interface HealthResponse {
  status: string;
  database: string;
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}

export async function startApplication(productCode?: string): Promise<TurnResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(productCode ? { product_code: productCode } : {}),
  });
  if (!response.ok) {
    throw new Error(`Failed to start application (status ${response.status})`);
  }
  return response.json() as Promise<TurnResponse>;
}

export async function sendMessage(sessionId: string, message: string): Promise<TurnResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error(`Failed to send message (status ${response.status})`);
  }
  return response.json() as Promise<TurnResponse>;
}

/** Returns null when the session id is unknown (404), so callers can start fresh. */
export async function getApplication(sessionId: string): Promise<ApplicationState | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications/${sessionId}`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to load application (status ${response.status})`);
  }
  return response.json() as Promise<ApplicationState>;
}

export async function listRequiredDocuments(sessionId: string): Promise<RequiredDocument[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications/${sessionId}/documents/required`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load required documents (status ${response.status})`);
  }
  const data = await response.json();
  return data.documents as RequiredDocument[];
}

export async function uploadNextDocument(
  sessionId: string,
  file: File,
): Promise<{ status: string; verification_type: string; reason?: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/applications/${sessionId}/documents/next`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Upload failed (status ${response.status})`);
  }
  return response.json();
}