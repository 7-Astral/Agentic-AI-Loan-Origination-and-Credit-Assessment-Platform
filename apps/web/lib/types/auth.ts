export type UserRole = "customer" | "loan_officer" | "credit_manager" | "admin";

export interface AuthenticatedUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  bank_id: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthenticatedUser;
}
