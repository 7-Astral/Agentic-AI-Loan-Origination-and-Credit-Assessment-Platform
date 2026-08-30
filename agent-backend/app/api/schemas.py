from typing import Any

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    product_code: str | None = None
    # product_code: str = Field(default="VL-NEW-020")


class SlotHint(BaseModel):
    id: str
    label: str
    type: str
    options: list[str] | None = None


class Progress(BaseModel):
    answered: int
    remaining_known: int
    current_phase: int | None
    complete: bool


class TurnResponse(BaseModel):
    session_id: str
    question: str | None
    slots_in_play: list[SlotHint] = []
    progress: Progress
    complete: bool
    escalated: bool = False


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ApplicationResponse(BaseModel):
    session_id: str
    product_code: str
    schema_version: str
    progress: Progress
    filled: dict[str, Any]
    provenance: dict[str, dict]
    transcript: list[dict]

class TurnResponse(BaseModel):
    session_id: str
    stage: str
    question: str | None
    slots_in_play: list[SlotHint] = []
    progress: Progress | None = None
    complete: bool
    escalated: bool = False
    product_code: str | None = None