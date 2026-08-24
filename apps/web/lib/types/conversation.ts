import type { LoanType } from "@/lib/types/bank";

export type ConversationStatus = "active" | "completed";
export type MessageRole = "user" | "assistant";

export interface ConversationMessage {
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface CreateConversationResponse {
  conversation_id: string;
  message: string;
}

export interface SendMessageResponse {
  message: string;
  current_question_index: number;
  total_questions: number;
  status: ConversationStatus;
  collected_data: Record<string, unknown>;
}

export interface ConversationState {
  id: string;
  bank_id: string;
  selected_loan_type: LoanType | null;
  selected_product_id: string | null;
  current_question_index: number;
  total_questions: number;
  collected_data: Record<string, unknown>;
  status: ConversationStatus;
  messages: ConversationMessage[];
}
