import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import handle_customer_message, start_conversation, total_questions_for
from core.database import get_db
from models.bank import Bank
from models.conversation import Conversation
from models.enums import MessageRole
from models.message import Message
from schemas.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationStateResponse,
    ConversationSummary,
    MessageCreateRequest,
    MessageCreateResponse,
    MessageOut,
    RequestDetailsRequest,
)

router = APIRouter(prefix="/agents/conversations", tags=["conversations"])

_FIVE_C_LABELS: dict[str, str] = {
    "character": "Character",
    "capacity": "Capacity",
    "capital": "Capital",
    "collateral": "Collateral",
    "conditions": "Conditions",
}

# Used only when no specific missing_fields were supplied — a generic ask for that C.
_FIVE_C_DEFAULT_ASK: dict[str, str] = {
    "character": "identity verification details so we can complete a credit check",
    "capacity": "recent proof of income and a summary of your monthly expenses",
    "capital": "evidence of your deposit or savings, e.g. a recent bank statement",
    "collateral": "details or a valuation of the asset being offered as security",
    "conditions": "further detail on the purpose of the loan and, if applicable, your business",
}


def _request_details_message(five_c: str, missing_fields: list[str]) -> str:
    label = _FIVE_C_LABELS.get(five_c, five_c.capitalize())
    ask = (
        ", ".join(missing_fields)
        if missing_fields
        else _FIVE_C_DEFAULT_ASK.get(five_c, "further details")
    )
    return (
        f"Following review of your application, we need some further details regarding "
        f"{label}. Could you please provide: {ask}?"
    )


async def _get_bank_or_404(db: AsyncSession, bank_id: uuid.UUID) -> Bank:
    bank = await db.get(Bank, bank_id)
    if bank is None:
        raise HTTPException(status_code=404, detail="Bank not found")
    return bank


async def _get_conversation_or_404(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[ConversationSummary]:
    stmt = (
        select(Conversation, Bank.name)
        .join(Bank, Conversation.bank_id == Bank.id)
        .where(Bank.is_test.is_(False), Conversation.hidden.is_(False))
        .order_by(Conversation.created_at.desc())
    )
    result = await db.execute(stmt)

    summaries = []
    for conversation, bank_name in result.all():
        total_questions = await total_questions_for(
            db, conversation.bank_id, conversation.selected_loan_type
        )
        summaries.append(
            ConversationSummary(
                id=conversation.id,
                bank_id=conversation.bank_id,
                bank_name=bank_name,
                selected_loan_type=conversation.selected_loan_type,
                status=conversation.status,
                current_question_index=conversation.current_question_index,
                total_questions=total_questions,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
        )
    return summaries


@router.post("", response_model=ConversationCreateResponse)
async def create_conversation(
    body: ConversationCreateRequest, db: AsyncSession = Depends(get_db)
) -> ConversationCreateResponse:
    bank = await _get_bank_or_404(db, body.bank_id)

    conversation = Conversation(bank_id=bank.id)
    db.add(conversation)
    await db.flush()

    greeting = await start_conversation(db, conversation, bank)
    await db.commit()

    return ConversationCreateResponse(conversation_id=conversation.id, message=greeting)


@router.post("/{conversation_id}/messages", response_model=MessageCreateResponse)
async def post_message(
    conversation_id: uuid.UUID,
    body: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageCreateResponse:
    conversation = await _get_conversation_or_404(db, conversation_id)
    bank = await _get_bank_or_404(db, conversation.bank_id)

    reply = await handle_customer_message(db, conversation, bank, body.content)
    total_questions = await total_questions_for(db, bank.id, conversation.selected_loan_type)

    await db.commit()

    return MessageCreateResponse(
        message=reply,
        current_question_index=conversation.current_question_index,
        total_questions=total_questions,
        status=conversation.status,
        collected_data=conversation.collected_data,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """Soft-delete: sets `hidden` rather than removing the row, so application data is
    never permanently lost — it just stops appearing in the Applications list."""
    conversation = await _get_conversation_or_404(db, conversation_id)
    conversation.hidden = True
    await db.commit()


@router.post(
    "/{conversation_id}/request-details",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def request_further_details(
    conversation_id: uuid.UUID,
    body: RequestDetailsRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    """No real email/notification channel exists yet — the request is appended to the
    conversation's own message thread instead, so the applicant sees it next time they
    open or resume their chat. Stand-in for a real notification, not a permanent design."""
    conversation = await _get_conversation_or_404(db, conversation_id)
    content = _request_details_message(body.five_c, body.missing_fields)
    message = Message(conversation_id=conversation.id, role=MessageRole.assistant, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageOut.model_validate(message)


@router.get("/{conversation_id}", response_model=ConversationStateResponse)
async def get_conversation(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ConversationStateResponse:
    conversation = await _get_conversation_or_404(db, conversation_id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    result = await db.execute(stmt)
    messages = [MessageOut.model_validate(m) for m in result.scalars().all()]

    total_questions = await total_questions_for(
        db, conversation.bank_id, conversation.selected_loan_type
    )

    return ConversationStateResponse(
        id=conversation.id,
        bank_id=conversation.bank_id,
        selected_loan_type=conversation.selected_loan_type,
        selected_product_id=conversation.selected_product_id,
        current_question_index=conversation.current_question_index,
        total_questions=total_questions,
        collected_data=conversation.collected_data,
        status=conversation.status,
        messages=messages,
    )
