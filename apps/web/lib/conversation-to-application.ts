import type { ConversationState } from "@/lib/types/conversation";

const LOAN_TYPE_DEFAULT_PURPOSE: Record<string, string> = {
  home: "Home purchase",
  investment: "Investment property purchase",
  car: "Vehicle purchase",
};

function loanPurposeFor(
  loanType: string | null,
  data: Record<string, unknown>,
): string | undefined {
  if (typeof data.loan_purpose === "string") return data.loan_purpose;
  if (typeof data.business_purpose === "string") return data.business_purpose;
  return loanType ? LOAN_TYPE_DEFAULT_PURPOSE[loanType] : undefined;
}

/** Maps a conversation's `collected_data` (from the loan-enquiry chat) into the raw
 * application shape the risk-assessment endpoint expects. The chat never asks for
 * name/dob/address, so Character will always come back `unavailable` for these — that's
 * accurate, not a bug: the assessment reflects what was actually collected. */
export function conversationToApplication(
  conversation: ConversationState,
): Record<string, unknown> {
  const data = conversation.collected_data;
  const loanType = conversation.selected_loan_type;

  const application: Record<string, unknown> = {
    applicant: {
      employment: {
        status: data.employment_status,
        income: data.annual_income,
        income_frequency: data.income_frequency,
      },
      monthly_expenses: data.monthly_expenses,
    },
    loan: {
      amount: data.loan_amount,
      purpose: loanPurposeFor(loanType, data),
      term_months: typeof data.loan_term_years === "number" ? data.loan_term_years * 12 : undefined,
      product_type: loanType ?? undefined,
      interest_only: loanType === "investment" ? data.interest_only : undefined,
      balloon_payment: loanType === "car" ? data.balloon_payment : undefined,
    },
  };

  const debtLoans: Record<string, unknown>[] = [];
  if (data.existing_debts === true && data.existing_debt_amount !== undefined) {
    debtLoans.push({ type: "combined existing debt", balance: data.existing_debt_amount });
  }
  if (
    loanType === "home" &&
    data.refinancing === true &&
    data.existing_mortgage_balance !== undefined
  ) {
    debtLoans.push({ type: "existing mortgage", balance: data.existing_mortgage_balance });
  }
  if (debtLoans.length > 0) {
    application.existing_debt = { loans: debtLoans };
  }

  if (loanType === "home" || loanType === "investment") {
    application.collateral = {
      asset_type: "Property",
      estimated_value: data.property_price,
      deposit_amount: data.deposit_amount,
    };
  } else if (loanType === "car") {
    // A trade-in reduces the amount financed the same way a deposit would.
    application.collateral = {
      asset_type: "Vehicle",
      estimated_value: data.vehicle_price,
      deposit_amount: data.trade_in_value,
    };
  } else if (loanType === "personal" && data.secured === true) {
    application.collateral = {
      asset_type: data.security_asset_type,
      estimated_value: data.security_asset_value,
    };
  }

  if (loanType === "business") {
    application.business = {
      abn: data.abn,
      entity_name: data.business_name,
      industry: data.industry,
      years_trading: data.years_trading,
      annual_turnover: data.annual_turnover,
      net_profit: data.net_profit,
      employee_count: data.employee_count,
    };
  }

  return application;
}
