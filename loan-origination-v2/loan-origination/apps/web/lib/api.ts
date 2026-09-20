import { handleExpiredSession } from "./session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  role: "customer" | "staff" | "admin";
  bank_id: string | null;
  position_id: string | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface DashboardStats {
  total_users: number;
  total_banks: number;
  total_loan_products: number;
  total_applications: number;
}

export interface BankOut {
  id: string;
  name: string;
  code: string;
  contact_email: string | null;
  status: string;
}

export interface LoanProductOut {
  id: string;
  bank_id: string;
  product_type: string;
  name: string;
  min_amount: number;
  max_amount: number;
  interest_rate_min: number;
  interest_rate_max: number;
  tenure_min_months: number;
  tenure_max_months: number;
  is_active: boolean;
}

export interface LendingPolicyOut {
  id: string;
  bank_id: string;
  product_id: string | null;
  auto_approval_max_amount: number;
  min_credit_score: number;
  max_dti_ratio: number;
  is_active: boolean;
}

export interface AuditLogOut {
  id: string;
  entity_type: string;
  entity_id: string;
  entity_label?: string | null;
  action: string;
  performed_by: string | null;
  created_at: string;
}

export interface BankPositionOut {
  id: string;
  bank_id: string;
  title: string;
  rank: number;
  max_approval_amount: number | null;
  can_manage_staff: boolean;
  can_manage_products: boolean;
}

export interface LoanApplicationOut {
  id: string;
  applicant_id: string;
  applicant_name?: string | null;
  applicant_email?: string | null;
  bank_id: string;
  product_id: string;
  loan_type: string;
  requested_amount: number;
  purpose: string | null;
  status: string;
  created_at: string;
  pending_position_title: string | null;
  chat_session_id: string | null;
}

export interface ChatReportTranscriptEntry {
  role: string;
  content: string;
  turn: number | null;
  created_at: string;
}

export interface ChatReportSlot {
  slot_key: string;
  value: unknown;
  source: string | null;
  turn: number | null;
}

export interface ChatReportAssessment {
  product_code: string;
  metrics: Record<string, { state: string; value: unknown; unit: string | null }>;
  metrics_computed: number;
  metrics_total: number;
  rule_results: Array<{ rule_id: string; status: string; message?: string }>;
  // Matches agent-backend's rules.engine.route(): a tier plus counts, not
  // an "outcome" field.
  route: {
    tier?: string;
    fail_count?: number;
    flag_count?: number;
    provisional_count?: number;
    [key: string]: unknown;
  };
  created_at: string;
}

export interface ChatReportDocument {
  document_id: string;
  verification_type: string;
  original_filename: string;
  content_type: string;
  status: string;
  uploaded_at: string;
  extraction: { extracted_fields: Record<string, unknown>; notes: string } | null;
  verifications: Array<{ slot_id: string; declared_value: string; extracted_value: string; status: string }>;
}

export interface ChatReportDecision {
  outcome: string;
  reasoning: string;
  decided_at: string;
}

export interface ChatReport {
  session_id: string;
  status: string;
  bank_id: string;
  applicant_id: string | null;
  product_code: string | null;
  platform_application_id: string | null;
  platform_status: string | null;
  created_at: string;
  updated_at: string;
  transcript: ChatReportTranscriptEntry[];
  slots: ChatReportSlot[];
  assessment: ChatReportAssessment | null;
  documents: ChatReportDocument[];
  decision: ChatReportDecision | null;
}

export interface ApplicationDecisionPayload {
  decision: "approved" | "rejected";
  reason?: string;
  approved_amount?: number;
}

export interface ApplicationDecisionOut {
  application_id: string;
  status: string;
  decision: string;
  decided_at: string;
}

export interface NotificationOut {
  id: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface CreateStaffPayload {
  email: string;
  password: string;
  full_name: string;
  bank_id: string;
  position_id?: string | null;
}

export interface CreateBankStaffPayload {
  email: string;
  password: string;
  full_name: string;
  position_id: string;
}

export interface UpdateBankStaffPayload {
  full_name?: string;
  position_id?: string;
}

export interface CreateBankPayload {
  name: string;
  code: string;
  contact_email?: string;
}

export interface CreateBankPositionPayload {
  title: string;
  rank: number;
  max_approval_amount?: number | null;
  can_manage_staff: boolean;
  can_manage_products: boolean;
}

export interface CreateLoanProductPayload {
  product_type: string;
  name: string;
  min_amount: number;
  max_amount: number;
  interest_rate_min: number;
  interest_rate_max: number;
  tenure_min_months: number;
  tenure_max_months: number;
}

export interface UpdateLoanProductPayload {
  product_type?: string;
  name?: string;
  min_amount?: number;
  max_amount?: number;
  interest_rate_min?: number;
  interest_rate_max?: number;
  tenure_min_months?: number;
  tenure_max_months?: number;
}

export interface CreateLendingPolicyPayload {
  product_id?: string | null;
  auto_approval_max_amount: number;
  min_credit_score: number;
  max_dti_ratio: number;
}

export interface UpdateLendingPolicyPayload {
  product_id?: string | null;
  auto_approval_max_amount?: number;
  min_credit_score?: number;
  max_dti_ratio?: number;
}

export interface LoanApplyPayload {
  bank_id: string;
  product_id: string;
  requested_amount: number;
  purpose?: string;
  tenure_requested_months: number;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse errors */
    }
    // Only an authenticated call going stale, not a failed login attempt
    // (which also returns 401 but never carries a token here).
    if (res.status === 401 && token) handleExpiredSession();
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  register: (email: string, password: string, full_name: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  me: (token: string) => request<UserOut>("/auth/me", {}, token),

  // Platform admin (cross-bank)
  dashboard: (token: string) => request<DashboardStats>("/admin/dashboard", {}, token),
  users: (token: string) => request<UserOut[]>("/admin/users", {}, token),
  banks: (token: string) => request<BankOut[]>("/admin/banks", {}, token),
  createBank: (token: string, payload: CreateBankPayload) =>
    request<BankOut>("/admin/banks", { method: "POST", body: JSON.stringify(payload) }, token),
  deactivateBank: (token: string, id: string) =>
    request<BankOut>(`/admin/banks/${id}/deactivate`, { method: "POST" }, token),
  reactivateBank: (token: string, id: string) =>
    request<BankOut>(`/admin/banks/${id}/reactivate`, { method: "POST" }, token),
  bankPositionsForAdmin: (token: string, bankId: string) =>
    request<BankPositionOut[]>(`/admin/banks/${bankId}/positions`, {}, token),
  createBankPositionForAdmin: (token: string, bankId: string, payload: CreateBankPositionPayload) =>
    request<BankPositionOut>(
      `/admin/banks/${bankId}/positions`,
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),
  loanProducts: (token: string) => request<LoanProductOut[]>("/admin/loan-products", {}, token),
  lendingPolicies: (token: string) => request<LendingPolicyOut[]>("/admin/lending-policies", {}, token),
  auditLogs: (token: string) => request<AuditLogOut[]>("/admin/audit-logs", {}, token),
  createStaff: (token: string, payload: CreateStaffPayload) =>
    request<UserOut>("/admin/staff", { method: "POST", body: JSON.stringify(payload) }, token),
  deactivateUser: (token: string, id: string) =>
    request<UserOut>(`/admin/users/${id}/deactivate`, { method: "POST" }, token),
  reactivateUser: (token: string, id: string) =>
    request<UserOut>(`/admin/users/${id}/reactivate`, { method: "POST" }, token),

  // Bank self-service (scoped to the logged-in staff member's own bank)
  bankPositions: (token: string) => request<BankPositionOut[]>("/bank/positions", {}, token),
  bankStaff: (token: string) => request<UserOut[]>("/bank/staff", {}, token),
  createBankStaff: (token: string, payload: CreateBankStaffPayload) =>
    request<UserOut>("/bank/staff", { method: "POST", body: JSON.stringify(payload) }, token),
  updateBankStaff: (token: string, id: string, payload: UpdateBankStaffPayload) =>
    request<UserOut>(`/bank/staff/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  deactivateBankStaff: (token: string, id: string) =>
    request<UserOut>(`/bank/staff/${id}/deactivate`, { method: "POST" }, token),
  reactivateBankStaff: (token: string, id: string) =>
    request<UserOut>(`/bank/staff/${id}/reactivate`, { method: "POST" }, token),
  bankProducts: (token: string) => request<LoanProductOut[]>("/bank/loan-products", {}, token),
  createBankProduct: (token: string, payload: CreateLoanProductPayload) =>
    request<LoanProductOut>("/bank/loan-products", { method: "POST", body: JSON.stringify(payload) }, token),
  updateBankProduct: (token: string, id: string, payload: UpdateLoanProductPayload) =>
    request<LoanProductOut>(`/bank/loan-products/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  deactivateBankProduct: (token: string, id: string) =>
    request<LoanProductOut>(`/bank/loan-products/${id}/deactivate`, { method: "POST" }, token),
  reactivateBankProduct: (token: string, id: string) =>
    request<LoanProductOut>(`/bank/loan-products/${id}/reactivate`, { method: "POST" }, token),
  bankPolicies: (token: string) => request<LendingPolicyOut[]>("/bank/lending-policies", {}, token),
  createBankPolicy: (token: string, payload: CreateLendingPolicyPayload) =>
    request<LendingPolicyOut>("/bank/lending-policies", { method: "POST", body: JSON.stringify(payload) }, token),
  updateBankPolicy: (token: string, id: string, payload: UpdateLendingPolicyPayload) =>
    request<LendingPolicyOut>(`/bank/lending-policies/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  deactivateBankPolicy: (token: string, id: string) =>
    request<LendingPolicyOut>(`/bank/lending-policies/${id}/deactivate`, { method: "POST" }, token),
  reactivateBankPolicy: (token: string, id: string) =>
    request<LendingPolicyOut>(`/bank/lending-policies/${id}/reactivate`, { method: "POST" }, token),
  bankApplications: (token: string) => request<LoanApplicationOut[]>("/bank/loan-applications", {}, token),
  bankChatReport: (token: string, applicationId: string) =>
    request<ChatReport>(`/bank/loan-applications/${applicationId}/chat-report`, {}, token),
  decideApplication: (token: string, applicationId: string, payload: ApplicationDecisionPayload) =>
    request<ApplicationDecisionOut>(
      `/bank/loan-applications/${applicationId}/decision`,
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),
  bankAuditLogs: (token: string) => request<AuditLogOut[]>("/bank/audit-logs", {}, token),
  notifications: (token: string) => request<NotificationOut[]>("/bank/notifications", {}, token),
  markNotificationRead: (token: string, id: string) =>
    request<NotificationOut>(`/bank/notifications/${id}/read`, { method: "POST" }, token),

  // Customer-facing loans
  browseProducts: () => request<LoanProductOut[]>("/loans/products"),
  applyForLoan: (token: string, payload: LoanApplyPayload) =>
    request<LoanApplicationOut>("/loans/apply", { method: "POST", body: JSON.stringify(payload) }, token),
  myApplications: (token: string) => request<LoanApplicationOut[]>("/loans/my-applications", {}, token),
};
