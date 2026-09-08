import type { RiskAssessmentReport } from "@/lib/types/risk-assessment";

export type ApplicationStatus = "draft" | "submitted" | "in_review" | "decided";
export type OfficerActionType = "approve" | "reject" | "override" | "request_info";
export type Outcome = "approved" | "rejected" | "overridden" | "info_requested";

export interface ApplicationSummary {
  id: string;
  bank_id: string;
  customer_id: string;
  customer_name: string;
  product_id: string;
  product_name: string;
  status: ApplicationStatus;
  loan_amount: string;
  loan_term_months: number;
  purpose: string | null;
  created_at: string;
  updated_at: string;
}

export interface OfficerActionOut {
  id: string;
  officer_id: string;
  officer_name: string;
  action: OfficerActionType;
  reason: string | null;
  created_at: string;
}

export interface CustomerProfileOut {
  employment_status: string | null;
  income: string | null;
  expenses: string | null;
  assets: Record<string, unknown>;
  liabilities: Record<string, unknown>;
}

export interface CustomerProfileUpdate {
  employment_status?: string | null;
  income?: number | null;
  expenses?: number | null;
  assets?: Record<string, unknown>;
  liabilities?: Record<string, unknown>;
}

/** Same shape for both roles, but the backend populates genuinely different fields per
 * role — a customer's response never carries `actions`, `customer_profile`, or
 * `risk_report`, and an officer's never carries `outcome`/`info_request_message`. See
 * services/api/routers/applications.py's `_build_customer_view` vs `_build_officer_view`. */
export interface ApplicationDetail extends ApplicationSummary {
  outcome: Outcome | null;
  info_request_message: string | null;
  actions: OfficerActionOut[];
  customer_profile: CustomerProfileOut | null;
  risk_report: RiskAssessmentReport | null;
}

export interface ApplicationActionRequest {
  action: OfficerActionType;
  reason?: string | null;
}
