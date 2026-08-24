import type { Bank } from "@/lib/types/bank";
import type {
  ConversationState,
  CreateConversationResponse,
  SendMessageResponse,
} from "@/lib/types/conversation";

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

/** Returns null for an unknown or inactive bank slug (404); throws on other failures. */
export async function getBank(slug: string): Promise<Bank | null> {
  const response = await fetch(`${API_BASE_URL}/banks/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to load bank "${slug}" (status ${response.status})`);
  }

  return response.json() as Promise<Bank>;
}

export async function createConversation(bankId: string): Promise<CreateConversationResponse> {
  const response = await fetch(`${API_BASE_URL}/agents/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bank_id: bankId }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start conversation (status ${response.status})`);
  }

  return response.json() as Promise<CreateConversationResponse>;
}

export async function sendConversationMessage(
  conversationId: string,
  content: string,
): Promise<SendMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/agents/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send message (status ${response.status})`);
  }

  return response.json() as Promise<SendMessageResponse>;
}

/** Returns null when the conversation id is unknown (404), so callers can start fresh. */
export async function getConversation(conversationId: string): Promise<ConversationState | null> {
  const response = await fetch(`${API_BASE_URL}/agents/conversations/${conversationId}`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to load conversation (status ${response.status})`);
  }

  return response.json() as Promise<ConversationState>;
}
