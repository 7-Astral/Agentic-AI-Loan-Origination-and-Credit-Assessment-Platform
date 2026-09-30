// Client for agent-backend's playground endpoints (/api/v1/playground/*):
// the Five C's assessment sandbox and the document extraction lab. These are
// developer tools, so unlike lib/agent-api.ts they send no auth token.
import type { DocumentOptions, ExtractRequest, ExtractResponse } from "@/lib/types/documents";
import type { AssessRequest, AssessResponse, PlaygroundOptions } from "@/lib/types/playground";

const AGENT_API_URL = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8001";

export async function getPlaygroundOptions(): Promise<PlaygroundOptions> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/playground/options`, { cache: "no-store" });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Failed to load playground options (status ${response.status})`);
  }
  return response.json() as Promise<PlaygroundOptions>;
}

export async function runPlaygroundAssessment(
  request: AssessRequest,
  signal?: AbortSignal,
): Promise<AssessResponse> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/playground/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Assessment failed (status ${response.status})`);
  }
  return response.json() as Promise<AssessResponse>;
}

export async function getDocumentOptions(): Promise<DocumentOptions> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/playground/documents/options`, { cache: "no-store" });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Failed to load document lab options (status ${response.status})`);
  }
  return response.json() as Promise<DocumentOptions>;
}

export function sampleDocumentUrl(sampleId: string): string {
  return `${AGENT_API_URL}/api/v1/playground/documents/samples/${sampleId}/file`;
}

export class ExtractionError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function extractDocument(request: ExtractRequest, signal?: AbortSignal): Promise<ExtractResponse> {
  const form = new FormData();
  form.append("verification_type", request.verificationType);
  form.append("declared", JSON.stringify(request.declared));
  form.append("live", String(request.live));
  form.append("categorize", String(request.categorize ?? true));
  if (request.sampleId) form.append("sample_id", request.sampleId);
  if (request.file && !request.sampleId) form.append("file", request.file);

  const response = await fetch(`${AGENT_API_URL}/api/v1/playground/documents/extract`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ExtractionError(detail?.detail ?? `Extraction failed (status ${response.status})`, response.status);
  }
  return response.json() as Promise<ExtractResponse>;
}
