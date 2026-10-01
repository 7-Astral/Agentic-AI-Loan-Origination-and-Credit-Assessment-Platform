import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.documents import list_required_documents, upload_document
from app.api.interview import _check_ownership
from app.api.schemas import InfoRequestCreate, InfoRequestOut, InfoRequestReply, OpenInfoRequestsOut
from app.core.db import get_session
from app.core.identity import get_customer_id_from_token
from app.core.service_auth import require_service_api_key
from app.models.application import Application, InformationRequest
from app.models.documents import Document
from app.services.storage import storage

router = APIRouter(prefix="/api/v1", tags=["info-requests"])


def _session_uuid(session_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(404, "Unknown session")


async def _document_names(request: Request, session_id: str, db: AsyncSession) -> dict[str, str]:
    try:
        required = await list_required_documents(request, session_id, db)
    except (HTTPException, httpx.HTTPError):
        return {}
    return {d["code"]: d["name"] for d in required["documents"]}


def _out(row: InformationRequest, names: dict[str, str]) -> InfoRequestOut:
    return InfoRequestOut(
        id=str(row.id),
        kind=row.kind,
        message=row.message,
        document_code=row.document_code,
        document_name=names.get(row.document_code) if row.document_code else None,
        requested_by=row.requested_by,
        status=row.status,
        response_text=row.response_text,
        document_id=str(row.document_id) if row.document_id else None,
        created_at=row.created_at,
        answered_at=row.answered_at,
    )


async def _list(request: Request, session_id: str, db: AsyncSession) -> list[InfoRequestOut]:
    result = await db.execute(
        select(InformationRequest)
        .where(InformationRequest.application_id == _session_uuid(session_id))
        .order_by(InformationRequest.created_at.asc())
    )
    rows = result.scalars().all()
    names = await _document_names(request, session_id, db) if rows else {}
    return [_out(row, names) for row in rows]


async def _open_request(db: AsyncSession, session_id: str, request_id: str) -> InformationRequest:
    try:
        row = await db.get(InformationRequest, uuid.UUID(request_id))
    except ValueError:
        raise HTTPException(404, "Unknown request")
    if row is None or row.application_id != _session_uuid(session_id):
        raise HTTPException(404, "Unknown request")
    if row.status != "open":
        raise HTTPException(409, "This request has already been answered")
    return row


@router.post(
    "/applications/{session_id}/info-requests",
    response_model=InfoRequestOut,
    status_code=201,
    dependencies=[Depends(require_service_api_key)],
)
async def create_info_request(
    request: Request, session_id: str, body: InfoRequestCreate, db: AsyncSession = Depends(get_session)
) -> InfoRequestOut:
    application = await db.get(Application, _session_uuid(session_id))
    if application is None:
        raise HTTPException(404, "Unknown session")
    if application.platform_application_id is None:
        raise HTTPException(409, "This application hasn't been submitted yet")

    row = InformationRequest(
        id=uuid.uuid4(),
        application_id=application.id,
        kind=body.kind,
        message=body.message.strip(),
        document_code=body.document_code if body.kind == "document" else None,
        requested_by=body.requested_by,
        status="open",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out(row, await _document_names(request, session_id, db))


@router.get(
    "/applications/{session_id}/info-requests/all",
    response_model=list[InfoRequestOut],
    dependencies=[Depends(require_service_api_key)],
)
async def list_info_requests_for_staff(
    request: Request, session_id: str, db: AsyncSession = Depends(get_session)
) -> list[InfoRequestOut]:
    return await _list(request, session_id, db)


@router.get("/info-requests/open", response_model=list[OpenInfoRequestsOut])
async def open_info_requests(
    authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_session)
) -> list[OpenInfoRequestsOut]:
    customer_id = get_customer_id_from_token(authorization)
    if not customer_id:
        raise HTTPException(401, "Sign in as a customer to see requests from the bank")

    result = await db.execute(
        select(InformationRequest, Application)
        .join(Application, Application.id == InformationRequest.application_id)
        .where(Application.applicant_id == uuid.UUID(customer_id), InformationRequest.status == "open")
        .order_by(InformationRequest.created_at.asc())
    )
    grouped: dict[uuid.UUID, OpenInfoRequestsOut] = {}
    for row, application in result.all():
        entry = grouped.get(application.id)
        if entry is None:
            grouped[application.id] = OpenInfoRequestsOut(
                session_id=str(application.id),
                product_code=application.product_code,
                open_count=1,
                latest_message=row.message,
            )
        else:
            entry.open_count += 1
            entry.latest_message = row.message
    return list(grouped.values())


@router.get("/applications/{session_id}/info-requests", response_model=list[InfoRequestOut])
async def list_info_requests(
    request: Request,
    session_id: str,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> list[InfoRequestOut]:
    await _check_ownership(session_id, authorization)
    return await _list(request, session_id, db)


@router.post("/applications/{session_id}/info-requests/{request_id}/reply", response_model=InfoRequestOut)
async def reply_to_info_request(
    request: Request,
    session_id: str,
    request_id: str,
    body: InfoRequestReply,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> InfoRequestOut:
    await _check_ownership(session_id, authorization)
    row = await _open_request(db, session_id, request_id)
    if row.kind != "information":
        raise HTTPException(400, "This request needs a document, not a message")

    row.response_text = body.message.strip()
    row.status = "answered"
    row.answered_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return _out(row, {})


@router.post("/applications/{session_id}/info-requests/{request_id}/document", status_code=201)
async def upload_for_info_request(
    request: Request,
    session_id: str,
    request_id: str,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> dict:
    await _check_ownership(session_id, authorization)
    row = await _open_request(db, session_id, request_id)
    if row.kind != "document":
        raise HTTPException(400, "This request needs a message, not a document")

    names = await _document_names(request, session_id, db)
    filename = file.filename or "upload"

    if row.document_code and row.document_code in names:
        result = await upload_document(
            request=request, session_id=session_id, verification_type=row.document_code, file=file, db=db,
        )
        if result["status"] == "needs_reupload":
            return result
        document_id = uuid.UUID(result["document_id"])
    else:
        content = await file.read()
        if not content:
            raise HTTPException(400, "Uploaded file is empty")
        document = Document(
            id=uuid.uuid4(),
            application_id=_session_uuid(session_id),
            verification_type=row.document_code or "additional",
            original_filename=filename,
            storage_path=await storage.save(session_id, filename, content),
            content_type=file.content_type or "application/octet-stream",
            status="uploaded",
        )
        db.add(document)
        await db.flush()
        document_id = document.id
        result = {
            "document_id": str(document.id),
            "verification_type": document.verification_type,
            "status": document.status,
        }

    row.document_id = document_id
    row.response_text = filename
    row.status = "answered"
    row.answered_at = datetime.now(timezone.utc)
    await db.commit()
    return result
