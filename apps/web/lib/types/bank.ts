export type LoanType = "home" | "investment" | "personal" | "car" | "business";

export interface BankBranding {
  primary_color: string;
  logo_url: string;
}

export interface LoanProduct {
  id: string;
  name: string;
  type: LoanType;
  interest_rate: string;
  min_amount: string;
  max_amount: string;
  min_term_months: number;
  max_term_months: number;
}

export interface Bank {
  id: string;
  name: string;
  slug: string;
  branding: BankBranding;
  products: LoanProduct[];
}
