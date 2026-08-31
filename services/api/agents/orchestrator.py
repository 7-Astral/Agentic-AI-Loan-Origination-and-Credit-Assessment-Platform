import json
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.clients.base import ChatMessage, LLMProvider
from agents.prompts.loader import get_active_prompt_template
from agents.prompts.renderer import render_prompt
from agents.questions.answer_resolver import resolve_answer
from agents.questions.loader import get_question_set
from agents.questions.sequencing import resolve_index
from models.bank import Bank
from models.conversation import Conversation
from models.enums import ConversationStatus, LoanType, MessageRole
from models.loan_product import LoanProduct
from models.message import Message
from schemas.question import Question

FALLBACK_SYSTEM_PROMPT = (
    "You are a loan broker for {{bank_name}}. Greet the customer and ask what they'd like "
    "the loan for. Available products:\n{{products}}"
)


def _format_products(products: list[LoanProduct]) -> str:
    if not products:
        return "(no products currently available)"
    lines = []
    for product in products:
        lines.append(
            f"- {product.name} ({product.type.value}): {product.interest_rate}% p.a., "
            f"${product.min_amount:,.0f}-${product.max_amount:,.0f}, "
            f"{product.min_term_months}-{product.max_term_months} months"
        )
    return "\n".join(lines)


def _format_transcript(history: list[ChatMessage]) -> str:
    lines = [f"{m['role']}: {m['content']}" for m in history]
    return "\n".join(lines) if lines else "(no messages yet)"


async def _load_products(db: AsyncSession, bank_id: uuid.UUID) -> list[LoanProduct]:
    stmt = select(LoanProduct).where(LoanProduct.bank_id == bank_id, LoanProduct.active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[ChatMessage]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    result = await db.execute(stmt)
    return [ChatMessage(role=m.role.value, content=m.content) for m in result.scalars().all()]


async def _system_prompt(db: AsyncSession, bank: Bank, products: list[LoanProduct]) -> str:
    template = await get_active_prompt_template(db, bank.id)
    content = template.content if template is not None else FALLBACK_SYSTEM_PROMPT
    return render_prompt(content, {"bank_name": bank.name, "products": _format_products(products)})


async def _identify_loan_type(
    llm: LLMProvider, history: list[ChatMessage], products: list[LoanProduct]
) -> LoanType | None:
    available = sorted({p.type.value for p in products})
    if not available:
        return None
    instruction = (
        "You are analyzing a customer's messages in a loan enquiry chat to determine which "
        f"loan type they want. Valid loan types: {', '.join(available)}. "
        'Reply with strict JSON only: {"loan_type": "<one of the valid types>"} if clear, '
        'or {"loan_type": null} if not yet clear. No other text.'
    )
    try:
        raw = await llm.extract(instruction, _format_transcript(history))
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    value = data.get("loan_type") if isinstance(data, dict) else None
    return LoanType(value) if value in available else None


def _match_product(products: list[LoanProduct], loan_type: LoanType) -> LoanProduct | None:
    for product in products:
        if product.type == loan_type:
            return product
    return None


def _stage2_directive(question: Question) -> str:
    return (
        "CURRENT INSTRUCTION: Ask the customer exactly this next question, phrased naturally "
        f'in your own words, and nothing else: "{question.prompt}"'
        + (f" (Options: {', '.join(question.options)})" if question.options else "")
    )


def _stage2_reask_directive(question: Question) -> str:
    return (
        "CURRENT INSTRUCTION: The customer's last reply didn't clearly answer the question. "
        f'Politely ask them to clarify this same question: "{question.prompt}"'
        + (f" (Options: {', '.join(question.options)})" if question.options else "")
    )


def _stage3_directive(collected_data: dict[str, Any], product: LoanProduct | None) -> str:
    product_line = f"Recommended product: {product.name}." if product is not None else ""
    return (
        "CURRENT INSTRUCTION: All questions are complete. Summarise back everything collected "
        f"below and the recommended product, then tell the customer a loan specialist will "
        f"review their enquiry.\n{product_line}\nCollected data: {json.dumps(collected_data)}"
    )


def _json_safe(value: Any) -> Any:
    """`collected_data` is stored as JSONB; Decimal (from currency/number answers) isn't
    JSON-serializable by the default encoder, so normalise it to a plain int/float."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


async def _save_message(
    db: AsyncSession, conversation_id: uuid.UUID, role: MessageRole, content: str
) -> None:
    db.add(Message(conversation_id=conversation_id, role=role, content=content))


async def start_conversation(
    db: AsyncSession, conversation: Conversation, bank: Bank, llm: LLMProvider | None = None
) -> str:
    """Generates and persists the agent's opening greeting for a brand-new conversation."""
    if llm is None:
        from agents.clients.factory import get_llm_provider

        llm = get_llm_provider()
    products = await _load_products(db, bank.id)
    system_prompt = await _system_prompt(db, bank, products)
    reply = await llm.complete(system_prompt, [])
    await _save_message(db, conversation.id, MessageRole.assistant, reply)
    return reply


async def handle_customer_message(
    db: AsyncSession,
    conversation: Conversation,
    bank: Bank,
    content: str,
    llm: LLMProvider | None = None,
) -> str:
    """Processes one customer message and returns the agent's reply, mutating `conversation`
    in place (caller is responsible for committing). The backend alone decides which
    question comes next and when the flow is complete — the model only phrases turns."""
    if llm is None:
        from agents.clients.factory import get_llm_provider

        llm = get_llm_provider()

    await _save_message(db, conversation.id, MessageRole.user, content)
    history = await _load_history(db, conversation.id)

    products = await _load_products(db, bank.id)
    system_prompt = await _system_prompt(db, bank, products)

    if conversation.selected_loan_type is None:
        loan_type = await _identify_loan_type(llm, history, products)

        if loan_type is None:
            reply = await llm.complete(system_prompt, history)
            await _save_message(db, conversation.id, MessageRole.assistant, reply)
            return reply

        product = _match_product(products, loan_type)
        conversation.selected_loan_type = loan_type
        conversation.selected_product_id = product.id if product else None

        questions = await get_question_set(db, bank.id, loan_type)
        index = resolve_index(questions, conversation.collected_data, 0)
        conversation.current_question_index = index

        if index >= len(questions):
            conversation.status = ConversationStatus.completed
            directive = _stage3_directive(conversation.collected_data, product)
        else:
            directive = _stage2_directive(questions[index])

        reply = await llm.complete(f"{system_prompt}\n\n{directive}", history)
        await _save_message(db, conversation.id, MessageRole.assistant, reply)
        return reply

    # Loan type already known — this message answers the current question.
    questions = await get_question_set(db, bank.id, conversation.selected_loan_type)
    index = resolve_index(
        questions, conversation.collected_data, conversation.current_question_index
    )
    product = _match_product(products, conversation.selected_loan_type)

    if index >= len(questions):
        conversation.status = ConversationStatus.completed
        directive = _stage3_directive(conversation.collected_data, product)
        reply = await llm.complete(f"{system_prompt}\n\n{directive}", history)
        await _save_message(db, conversation.id, MessageRole.assistant, reply)
        return reply

    current_question = questions[index]
    accepted, value = await resolve_answer(current_question, content, llm)

    if accepted:
        conversation.collected_data = {
            **conversation.collected_data,
            current_question.key: _json_safe(value),
        }
        new_index = resolve_index(questions, conversation.collected_data, index + 1)
        conversation.current_question_index = new_index

        if new_index >= len(questions):
            conversation.status = ConversationStatus.completed
            directive = _stage3_directive(conversation.collected_data, product)
        else:
            directive = _stage2_directive(questions[new_index])
    else:
        directive = _stage2_reask_directive(current_question)

    reply = await llm.complete(f"{system_prompt}\n\n{directive}", history)
    await _save_message(db, conversation.id, MessageRole.assistant, reply)
    return reply


async def total_questions_for(
    db: AsyncSession, bank_id: uuid.UUID, loan_type: LoanType | None
) -> int:
    if loan_type is None:
        return 0
    questions = await get_question_set(db, bank_id, loan_type)
    return len(questions)
