import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.assessment.run import run_assessment
from app.agents.interaction.advisor import answer_question
from app.agents.interaction.corrections import apply_correction
from app.agents.interaction.prefill import load_profile_prefill
from app.agents.interaction.resolver import progress as compute_progress
from app.api.schemas import (
    ApplicationResponse,
    ChatMessageOut,
    ResumeResponse,
    MessageRequest,
    ProductOption,
    Progress,
    SlotHint,
    StartRequest,
    TurnResponse,
)
from app.core.config import get_settings
from app.core.db import get_session
from app.core.identity import get_customer_id_from_token
from app.services.core_banking import core_banking

logger = logging.getLogger(__name__)
from app.services.operational import (
    ensure_application,
    latest_open_session,
    get_applicant_id,
    get_bank_id,
    is_submitted,
    mirror_transcript,
    mirror_turn,
    record_platform_submission,
    set_application_product,
)

router = APIRouter(prefix="/api/v1/applications", tags=["interview"])

def _discovery_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": f"{session_id}:discovery"}}


def _interview_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": f"{session_id}:interview"}}

def _hints(batch: list[dict]) -> list[SlotHint]:
    return [
        SlotHint(id=s["id"], label=s["label"], type=s["type"], options=s.get("options"))
        for s in batch
    ]


def _interrupt_payload(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__")
    return interrupts[0].value if interrupts else None


def _pending_payload(snapshot) -> dict | None:
    for task in snapshot.tasks or ():
        for interrupt in getattr(task, "interrupts", ()) or ():
            return interrupt.value
    return None


async def _discovery_length(request: Request, session_id: str) -> int:
    snapshot = await request.app.state.discovery_graph.aget_state(_discovery_config(session_id))
    return len((snapshot.values or {}).get("transcript") or [])


async def _resolve_stage(request: Request, session_id: str) -> str | None:
    interview_snapshot = await request.app.state.interview_graph.aget_state(
        _interview_config(session_id)
    )
    if interview_snapshot.values:
        return "complete" if not interview_snapshot.next else "interview"

    discovery_snapshot = await request.app.state.discovery_graph.aget_state(
        _discovery_config(session_id)
    )
    if discovery_snapshot.values:
        return "discovery"

    return None


async def _load_schema(product_code: str, bank_id: str) -> dict:
    try:
        return await core_banking.get_product_requirements(product_code, bank_id=bank_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, f"Unknown product '{product_code}'")
        raise HTTPException(502, "Core banking API error") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Core banking API unavailable") from exc


async def _start_interview(request: Request, session_id: str, product_code: str) -> TurnResponse:
    interview_graph = request.app.state.interview_graph
    bank_id = await get_bank_id(session_id)
    schema = await _load_schema(product_code, bank_id)
    await set_application_product(session_id, product_code)
    filled, provenance = await load_profile_prefill(await get_applicant_id(session_id), schema["slots"])

    result = await interview_graph.ainvoke(
        {
            "product_code": schema["product_code"],
            "schema_version": schema["schema_version"],
            "slots": schema["slots"],
            "filled": filled,
            "provenance": provenance,
            "turn": 0,
        },
        _interview_config(session_id),
    )
    return await _interview_turn(request, session_id, result)


async def _interview_turn(request: Request, session_id: str, result: dict) -> TurnResponse:
    interview_graph = request.app.state.interview_graph
    snapshot = await interview_graph.aget_state(_interview_config(session_id))
    values = snapshot.values
    payload = _interrupt_payload(result)
    complete = payload is None

    await mirror_turn(session_id, values, complete, transcript_offset=await _discovery_length(request, session_id))

    return TurnResponse(
        session_id=session_id,
        stage="complete" if complete else "interview",
        question=payload.get("question") if payload else None,
        slots_in_play=_hints(values.get("current_batch") or []) if payload else [],
        progress=Progress(
            **compute_progress(values["slots"], values.get("filled") or {})
        ),
        complete=complete,
        escalated=bool(values.get("escalate")),
        product_code=values.get("product_code"),
    )


def _product_options(state_products: list[dict] | None) -> list[ProductOption] | None:
    if not state_products:
        return None
    return [
        ProductOption(
            product_code=p["product_code"],
            name=p["name"],
            interest_rate=p.get("interest_rate"),
            comparison_rate=p.get("comparison_rate"),
            rate_type=p.get("rate_type"),
            min_amount=p["min_amount"],
            max_amount=p["max_amount"],
            min_term_months=p["min_term_months"],
            max_term_months=p["max_term_months"],
            features=p.get("features") or [],
        )
        for p in state_products
    ]


async def _discovery_turn(request: Request, session_id: str, result: dict) -> TurnResponse:
    discovery_graph = request.app.state.discovery_graph
    payload = _interrupt_payload(result)

    snapshot = await discovery_graph.aget_state(_discovery_config(session_id))
    await mirror_transcript(session_id, snapshot.values.get("transcript") or [], snapshot.values.get("turn"))

    if payload is None:
        # Discovery finished — hand off to the interview.
        product_code = snapshot.values.get("product_code")
        if not product_code:
            raise HTTPException(500, "Discovery ended without a product")
        return await _start_interview(request, session_id, product_code)

    stage = payload.get("stage", "discovery")
    return TurnResponse(
        session_id=session_id,
        stage=stage,
        question=payload.get("question"),
        complete=False,
        products=_product_options(payload.get("products")) if stage == "product_selection" else None,
    )


@router.post("", response_model=TurnResponse)
async def start_application(
    request: Request, body: StartRequest, authorization: str | None = Header(default=None)
) -> TurnResponse:
    session_id = str(uuid.uuid4())
    bank_id = body.bank_id or get_settings().platform_bank_id
    if not bank_id:
        try:
            bank_id = await core_banking.resolve_default_bank_id()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                502,
                "Couldn't resolve the platform bank — check that PLATFORM_BANK_CODE "
                "matches a real bank's code in services/api.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Core banking API unavailable while resolving the platform bank") from exc
    applicant_id = get_customer_id_from_token(authorization)
    await ensure_application(session_id, bank_id=bank_id, applicant_id=applicant_id)

    if body.product_code:
        return await _start_interview(request, session_id, body.product_code)

    discovery_graph = request.app.state.discovery_graph
    bank_id = await get_bank_id(session_id)
    result = await discovery_graph.ainvoke({"turn": 0, "bank_id": bank_id}, _discovery_config(session_id))
    return await _discovery_turn(request, session_id, result)


def _display(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
    return str(value).replace("_", " ")


def _correction_note(slots: list[dict], outcome: dict) -> str:
    labels = {s["id"]: s["label"] for s in slots}
    parts = []
    if outcome["changed"]:
        lines = []
        for slot_id, value in outcome["changed"].items():
            previous = outcome["previous"].get(slot_id)
            label = labels.get(slot_id, slot_id)
            if previous is None:
                lines.append(f"- **{label}**: {_display(value)}")
            else:
                lines.append(f"- **{label}**: {_display(previous)} → {_display(value)}")
        parts.append("I've updated your application:\n\n" + "\n".join(lines))
    if outcome["errors"]:
        parts.append("I couldn't change this — " + "; ".join(outcome["errors"]) + ".")
    return "\n\n".join(parts)


async def _answer(session_id: str, values: dict, message: str) -> str:
    product = None
    try:
        product = await core_banking.get_product(values["product_code"], bank_id=await get_bank_id(session_id))
    except (httpx.HTTPError, KeyError):
        pass
    return await answer_question(
        message, product, values["slots"], values.get("filled") or {}, values.get("transcript") or []
    )


async def _correction_turn(request: Request, session_id: str, message: str) -> TurnResponse:
    graph = request.app.state.interview_graph
    config = _interview_config(session_id)
    snapshot = await graph.aget_state(config)
    values = snapshot.values

    outcome = await apply_correction(values, message)
    if outcome["changed"] or outcome["errors"]:
        note = _correction_note(values["slots"], outcome)
    else:
        note = await _answer(session_id, values, message)

    update = {
        "filled": outcome["changed"],
        "provenance": outcome["provenance"],
        "turn": outcome["turn"],
        "transcript": [
            {"role": "user", "content": message},
            {"role": "assistant", "content": note},
        ],
    }
    if values.get("escalate"):
        await graph.aupdate_state(config, update, as_node="finish")
        result: dict = {}
    else:
        update.update({"repair": False, "last_error": None, "pending_question": None})
        await graph.aupdate_state(config, update, as_node="ingest")
        result = await graph.ainvoke(None, config)

    response = await _interview_turn(request, session_id, result)
    response.note = note
    return response


async def _check_ownership(session_id: str, authorization: str | None) -> None:
    token_customer_id = get_customer_id_from_token(authorization)
    owner_id = await get_applicant_id(session_id)
    if owner_id and token_customer_id and owner_id != token_customer_id:
        raise HTTPException(403, "This application belongs to a different customer")


@router.post("/{session_id}/messages", response_model=TurnResponse)
async def send_message(
    request: Request, session_id: str, body: MessageRequest, authorization: str | None = Header(default=None)
) -> TurnResponse:
    await _check_ownership(session_id, authorization)
    stage = await _resolve_stage(request, session_id)
    if stage is None:
        raise HTTPException(404, "Unknown session")
    if stage == "complete":
        if await is_submitted(session_id):
            raise HTTPException(409, "This application has already been submitted to the bank")
        return await _correction_turn(request, session_id, body.message)

    if stage == "discovery":
        graph, config = request.app.state.discovery_graph, _discovery_config(session_id)
        result = await graph.ainvoke(Command(resume=body.message), config)
        return await _discovery_turn(request, session_id, result)

    graph, config = request.app.state.interview_graph, _interview_config(session_id)
    result = await graph.ainvoke(Command(resume=body.message), config)
    return await _interview_turn(request, session_id, result)


@router.post("/{session_id}/submit")
async def submit_application(
    request: Request, session_id: str, authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> dict:
    await _check_ownership(session_id, authorization)
    stage = await _resolve_stage(request, session_id)
    if stage is None:
        raise HTTPException(404, "Unknown session")
    if stage != "complete":
        raise HTTPException(409, "The interview isn't complete yet")

    applicant_id = get_customer_id_from_token(authorization) or await get_applicant_id(session_id)
    if not applicant_id:
        raise HTTPException(401, "Sign in as a customer to submit this application")

    interview_graph = request.app.state.interview_graph
    snapshot = await interview_graph.aget_state(_interview_config(session_id))
    values = snapshot.values
    filled = values.get("filled") or {}
    product_code = values.get("product_code")
    if not product_code or "loan_amount" not in filled or "loan_term_months" not in filled:
        raise HTTPException(409, "Missing required loan details — the interview may not be complete")

    score_report: dict = {}
    try:
        assessment = await run_assessment(interview_graph, _interview_config(session_id), db, session_id)
        score_report = assessment.get("score_report") or {}
    except Exception:
        logger.exception("Five C's assessment failed for session %s — continuing with submission", session_id)

    bank_id = await get_bank_id(session_id)
    purpose = filled.get("purpose_detail") or filled.get("loan_purpose")

    try:
        result = await core_banking.catalog.submit_application(
            bank_id=bank_id,
            applicant_id=applicant_id,
            product_code=product_code,
            requested_amount=float(filled["loan_amount"]),
            tenure_requested_months=int(filled["loan_term_months"]),
            purpose=str(purpose) if purpose else None,
            external_reference=session_id,
            applicant_legal_name=filled.get("full_name"),
            assessment_tier=score_report.get("tier"),
            assessment_score=score_report.get("overall_score"),
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        raise HTTPException(502, f"The bank rejected this application: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(503, "The bank's application service is unavailable") from exc

    await record_platform_submission(session_id, result["application_id"], result["status"])
    return result


@router.get("/current", response_model=ResumeResponse)
async def current_application(request: Request, authorization: str | None = Header(default=None)) -> ResumeResponse:
    customer_id = get_customer_id_from_token(authorization)
    if not customer_id:
        raise HTTPException(401, "Sign in as a customer to resume an application")
    session_id = await latest_open_session(customer_id)
    if session_id is None:
        raise HTTPException(404, "No application in progress")
    return await _resume_response(request, session_id)


@router.get("/{session_id}/resume", response_model=ResumeResponse)
async def resume_application(
    request: Request, session_id: str, authorization: str | None = Header(default=None)
) -> ResumeResponse:
    await _check_ownership(session_id, authorization)
    if await _resolve_stage(request, session_id) is None:
        raise HTTPException(404, "Unknown session")
    return await _resume_response(request, session_id)


async def _resume_response(request: Request, session_id: str) -> ResumeResponse:
    submitted = await is_submitted(session_id)
    discovery =await request.app.state.discovery_graph.aget_state(_discovery_config(session_id))
    interview = await request.app.state.interview_graph.aget_state(_interview_config(session_id))
    transcript = list((discovery.values or {}).get("transcript") or []) + list(
        (interview.values or {}).get("transcript") or []
    )
    messages = [ChatMessageOut(role=m.get("role", ""), content=m.get("content", "")) for m in transcript]

    if interview.values:
        values = interview.values
        payload = _pending_payload(interview)
        complete = not interview.next
        return ResumeResponse(
            session_id=session_id,
            stage="complete" if complete else "interview",
            question=None if complete or payload is None else payload.get("question"),
            slots_in_play=[] if complete else _hints(values.get("current_batch") or []),
            progress=Progress(**compute_progress(values["slots"], values.get("filled") or {})),
            complete=complete,
            product_code=values.get("product_code"),
            messages=messages,
            submitted=submitted,
        )

    if discovery.values:
        payload = _pending_payload(discovery) or {}
        stage = payload.get("stage", "discovery")
        return ResumeResponse(
            session_id=session_id,
            stage=stage,
            question=payload.get("question"),
            complete=False,
            products=_product_options(payload.get("products")) if stage == "product_selection" else None,
            messages=messages,
        )

    raise HTTPException(404, "No application in progress")


@router.get("/{session_id}", response_model=ApplicationResponse)
async def get_application(
    request: Request, session_id: str, authorization: str | None = Header(default=None)
) -> ApplicationResponse:
    await _check_ownership(session_id, authorization)
    stage = await _resolve_stage(request, session_id)
    if stage is None:
        raise HTTPException(404, "Unknown session")
    if stage == "discovery":
        raise HTTPException(409, "No application yet — still choosing a product")

    interview_graph = request.app.state.interview_graph
    snapshot = await interview_graph.aget_state(_interview_config(session_id))
    values = snapshot.values

    return ApplicationResponse(
        session_id=session_id,
        product_code=values.get("product_code", ""),
        schema_version=values.get("schema_version", ""),
        progress=Progress(
            **compute_progress(values["slots"], values.get("filled") or {})
        ),
        filled=values.get("filled") or {},
        provenance=values.get("provenance") or {},
        transcript=values.get("transcript") or [],
    )