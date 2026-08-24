import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from models.enums import ConversationStatus, LoanType, MessageRole


class ConversationCreateRequest(BaseModel):
    bank_id: uuid.UUID


class ConversationCreateResponse(BaseModel):
    conversation_id: uuid.UUID
    message: str


class MessageCreateRequest(BaseModel):
    content: str


class MessageCreateResponse(BaseModel):
    message: str
    current_question_index: int
    total_questions: int
    status: ConversationStatus
    collected_data: dict[str, Any]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: MessageRole
    content: str
    created_at: datetime


class ConversationStateResponse(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    selected_loan_type: LoanType | None
    selected_product_id: uuid.UUID | None
    current_question_index: int
    total_questions: int
    collected_data: dict[str, Any]
    status: ConversationStatus
    messages: list[MessageOut]
