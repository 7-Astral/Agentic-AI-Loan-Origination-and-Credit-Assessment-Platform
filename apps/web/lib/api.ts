import { getToken } from "@/lib/auth";
import type {
  ApplicationActionRequest,
  ApplicationDetail,
  ApplicationStatus,
  ApplicationSummary,
  CustomerProfileOut,
  CustomerProfileUpdate,
} from "@/lib/types/application";
import type { AuthenticatedUser, LoginResponse } from "@/lib/types/auth";
import type { Bank } from "@/lib/types/bank";
import type {
  ConversationState,
  ConversationSummary,
  CreateConversationResponse,
  SendMessageResponse,
} from "@/lib/types/conversation";
import type { FiveCKey, RiskAssessmentReport } from "@/lib/types/risk-assessment";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

/** Carries the HTTP status alongside the backend's `detail` message so callers can show a
 * real error ("Invalid email or password", "A reason is required for this action") instead
 * of a generic failure string. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function errorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Response body wasn't JSON (or had no `detail`) — fall back below.
  }
  return fallback;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

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

export async function listConversations(): Promise<ConversationSummary[]> {
  const response = await fetch(`${API_BASE_URL}/agents/conversations`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Failed to load applications (status ${response.status})`);
  }

  return response.json() as Promise<ConversationSummary[]>;
}

/** Soft-delete: the application stops appearing in listConversations(), but its data
 * isn't removed from the database. */
export async function deleteApplication(conversationId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/agents/conversations/${conversationId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete application (status ${response.status})`);
  }
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

/** No real email/notification channel exists yet — this appends a message to the
 * conversation's own chat thread, which the applicant sees next time they open or resume
 * their chat. Stand-in for a real notification, not a permanent design. */
export async function requestFurtherDetails(
  conversationId: string,
  fiveC: FiveCKey,
  missingFields: string[],
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/agents/conversations/${conversationId}/request-details`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ five_c: fiveC, missing_fields: missingFields }),
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to request further details (status ${response.status})`);
  }
}

export async function assessRisk(
  application: Record<string, unknown>,
): Promise<RiskAssessmentReport> {
  const response = await fetch(`${API_BASE_URL}/risk-assessment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ application }),
  });

  if (!response.ok) {
    throw new Error(`Failed to assess application (status ${response.status})`);
  }

  return response.json() as Promise<RiskAssessmentReport>;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response, "Login failed"));
  }

  return response.json() as Promise<LoginResponse>;
}

export async function register(input: {
  name: string;
  email: string;
  password: string;
  bank_id: string;
}): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response, "Registration failed"));
  }

  return response.json() as Promise<LoginResponse>;
}

/** The backend endpoint exists for symmetry/future revocation; discarding the local token
 * (see lib/auth.ts's clearAuth) is what actually logs the user out today. */
export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", headers: authHeaders() });
}

export async function getMe(): Promise<AuthenticatedUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to load the current user");
  }

  return response.json() as Promise<AuthenticatedUser>;
}

/** Same endpoint for every role — the backend scopes the result by the authenticated
 * identity, never by a client-supplied filter. `status` only has an effect for
 * officer/credit_manager callers. */
export async function listApplications(status?: ApplicationStatus): Promise<ApplicationSummary[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const response = await fetch(`${API_BASE_URL}/applications${query}`, {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to load applications");
  }

  return response.json() as Promise<ApplicationSummary[]>;
}

export async function getApplication(applicationId: string): Promise<ApplicationDetail> {
  const response = await fetch(`${API_BASE_URL}/applications/${applicationId}`, {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to load the application");
  }

  return response.json() as Promise<ApplicationDetail>;
}

export async function postApplicationAction(
  applicationId: string,
  body: ApplicationActionRequest,
): Promise<ApplicationDetail> {
  const response = await fetch(`${API_BASE_URL}/applications/${applicationId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response, "Couldn't record that action"));
  }

  return response.json() as Promise<ApplicationDetail>;
}

export async function getMyProfile(): Promise<CustomerProfileOut> {
  const response = await fetch(`${API_BASE_URL}/users/me/profile`, {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to load your profile");
  }

  return response.json() as Promise<CustomerProfileOut>;
}

export async function patchMyProfile(body: CustomerProfileUpdate): Promise<CustomerProfileOut> {
  const response = await fetch(`${API_BASE_URL}/users/me/profile`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response, "Failed to update your profile"));
  }

  return response.json() as Promise<CustomerProfileOut>;
}
