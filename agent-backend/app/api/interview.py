import uuid

import httpx
from fastapi import APIRouter, HTTPException, Request
from langgraph.types import Command

from app.agents.interaction.resolver import progress as compute_progress
from app.api.schemas import (
    ApplicationResponse,
    MessageRequest,
    Progress,
    SlotHint,
    StartRequest,
    TurnResponse,
)
from app.services.core_banking import core_banking

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


async def _load_schema(product_code: str) -> dict:
    try:
        return await core_banking.get_product_requirements(product_code)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, f"Unknown product '{product_code}'")
        raise HTTPException(502, "Core banking API error") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Core banking API unavailable") from exc


async def _start_interview(request: Request, session_id: str, product_code: str) -> TurnResponse:
    interview_graph = request.app.state.interview_graph
    schema = await _load_schema(product_code)

    result = await interview_graph.ainvoke(
        {
            "product_code": schema["product_code"],
            "schema_version": schema["schema_version"],
            "slots": schema["slots"],
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


async def _discovery_turn(request: Request, session_id: str, result: dict) -> TurnResponse:
    discovery_graph = request.app.state.discovery_graph
    payload = _interrupt_payload(result)

    if payload is None:
        # Discovery finished — hand off to the interview.
        snapshot = await discovery_graph.aget_state(_discovery_config(session_id))
        product_code = snapshot.values.get("product_code")
        if not product_code:
            raise HTTPException(500, "Discovery ended without a product")
        return await _start_interview(request, session_id, product_code)

    return TurnResponse(
        session_id=session_id,
        stage=payload.get("stage", "discovery"),
        question=payload.get("question"),
        complete=False,
    )


@router.post("", response_model=TurnResponse)
async def start_application(request: Request, body: StartRequest) -> TurnResponse:
    session_id = str(uuid.uuid4())

    if body.product_code:
        return await _start_interview(request, session_id, body.product_code)

    discovery_graph = request.app.state.discovery_graph
    result = await discovery_graph.ainvoke({"turn": 0}, _discovery_config(session_id))
    return await _discovery_turn(request, session_id, result)


@router.post("/{session_id}/messages", response_model=TurnResponse)
async def send_message(request: Request, session_id: str, body: MessageRequest) -> TurnResponse:
    stage = await _resolve_stage(request, session_id)
    if stage is None:
        raise HTTPException(404, "Unknown session")
    if stage == "complete":
        raise HTTPException(409, "This application is already complete")

    if stage == "discovery":
        graph, config = request.app.state.discovery_graph, _discovery_config(session_id)
        result = await graph.ainvoke(Command(resume=body.message), config)
        return await _discovery_turn(request, session_id, result)

    graph, config = request.app.state.interview_graph, _interview_config(session_id)
    result = await graph.ainvoke(Command(resume=body.message), config)
    return await _interview_turn(request, session_id, result)


@router.get("/{session_id}", response_model=ApplicationResponse)
async def get_application(request: Request, session_id: str) -> ApplicationResponse:
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