from typing import Any

from pydantic import BaseModel


class SlotExtraction(BaseModel):
    values: dict[str, Any] | None = None
    unclear: list[str] | None = None
    notes: str | None = None


class LoanTypeChoice(BaseModel):
    loan_type: str | None = None
    confidence: str | None = None
    reply_to_question: str | None = None


class CategoryChoice(BaseModel):
    category: str | None = None
    confidence: str | None = None
    reply_to_question: str | None = None


class ProductChoice(BaseModel):
    product_code: str | None = None
    reply_to_question: str | None = None


class CategorizedTransaction(BaseModel):
    index: int
    category: str


class TransactionCategories(BaseModel):
    categorized: list[CategorizedTransaction] = []


class DocumentExtraction(BaseModel):
    matches_claimed_type: bool = False
    fields: dict[str, Any] | None = None
    notes: str | None = None
