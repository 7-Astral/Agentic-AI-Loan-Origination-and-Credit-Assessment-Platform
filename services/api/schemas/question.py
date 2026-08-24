from enum import Enum
from typing import Any

from pydantic import BaseModel


class QuestionType(str, Enum):
    currency = "currency"
    number = "number"
    integer = "integer"
    text = "text"
    choice = "choice"
    boolean = "boolean"


class QuestionValidation(BaseModel):
    min: float | None = None
    max: float | None = None


class QuestionDependsOn(BaseModel):
    key: str
    equals: Any


class Question(BaseModel):
    key: str
    prompt: str
    type: QuestionType
    required: bool = True
    validation: QuestionValidation | None = None
    help_text: str | None = None
    options: list[str] | None = None
    depends_on: QuestionDependsOn | None = None
