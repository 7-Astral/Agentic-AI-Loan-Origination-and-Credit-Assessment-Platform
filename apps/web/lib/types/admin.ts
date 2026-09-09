export interface AdminBank {
  id: string;
  name: string;
  slug: string;
  primaryColor: string;
  status: "active" | "draft";
  createdAt: string;
}

export interface AdminCategory {
  code: string;
  name: string;
}

export interface AdminLoanType {
  code: string;
  name: string;
  description: string;
  categories: AdminCategory[];
}

export interface AdminProduct {
  productCode: string;
  name: string;
  loanTypeCode: string;
  categoryCode: string;
  secured: boolean;
  minAmount: number;
  maxAmount: number;
  minTermMonths: number;
  maxTermMonths: number;
  interestRate: number;
  comparisonRate: number;
  rateType: "fixed" | "variable";
  establishmentFee: number;
  maxLvr: number | null;
  features: string[];
}

export interface AdminDocumentType {
  code: string;
  name: string;
}

export interface AdminDocumentRequirement {
  loanTypeCode: string;
  categoryCode: string;
  documentTypeCode: string;
}

export interface AdminLoanPolicyRow {
  loanTypeCode: string;
  categoryCode: string;
  minAge: string;
  residencyPolicy: string;
  depositLvrPolicy: string;
  loanAmountRange: string;
  maxTerm: string;
  incomeCashFlowPolicy: string;
  serviceabilityPolicy: string;
  creditPolicy: string;
}

export type AdminPolicyVersionStatus = "active" | "superseded";

export interface AdminPolicyVersion {
  id: string;
  version: string;
  status: AdminPolicyVersionStatus;
  effectiveFrom: string;
  createdAt: string;
  notes: string;
  loanPolicyRows: AdminLoanPolicyRow[];
}

export type AdminRuleStatus = "fail" | "flag" | "pass";

export type AdminRuleFramework = "individual" | "business";

export interface AdminRule {
  ruleId: string;
  framework: AdminRuleFramework;
  requires: string[];
  when: string;
  status: AdminRuleStatus;
  message: string;
}
export type AdminAuditEventType = "llm_call" | "decision" | "document" | "admin_change";

interface AdminAuditEventBase {
  id: string;
  timestamp: string;
  applicationId?: string;
  summary: string;
}

export interface AdminLlmCallAuditEvent extends AdminAuditEventBase {
  type: "llm_call";
  agent: string;
  model: string;
  purpose: string;
  latencyMs: number;
  status: "success" | "retry" | "error";
}

export interface AdminDecisionAuditEvent extends AdminAuditEventBase {
  type: "decision";
  stage: string;
  outcome: string;
}

export interface AdminDocumentAuditEvent extends AdminAuditEventBase {
  type: "document";
  documentType: string;
  action: "uploaded" | "extracted" | "reconciled";
  outcome?: string;
}

export interface AdminChangeAuditEvent extends AdminAuditEventBase {
  type: "admin_change";
  entity: string;
  action: "created" | "updated" | "deleted";
  actor: string;
}

export type AdminAuditEvent =
  | AdminLlmCallAuditEvent
  | AdminDecisionAuditEvent
  | AdminDocumentAuditEvent
  | AdminChangeAuditEvent;
