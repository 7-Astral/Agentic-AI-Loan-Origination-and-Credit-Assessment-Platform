import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import handle_customer_message, start_conversation, total_questions_for
from core.database import get_db
from models.bank import Bank
from models.conversation import Conversation
from models.message import Message
from schemas.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationStateResponse,
    MessageCreateRequest,
    MessageCreateResponse,
    MessageOut,
)

router = APIRouter(prefix="/agents/conversations", tags=["conversations"])


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
