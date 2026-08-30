import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.document.reconcile import reconcile
from app.models.documents import Document, DocumentExtraction, VerificationResult
from app.api.interview import _interview_config, _resolve_stage
from app.core.db import get_session
from app.models.documents import Document
from app.services.core_banking import core_banking
from app.services.storage import storage
from app.agents.document.extractor import extract as extract_document
from app.models.documents import Document, DocumentExtraction

router = APIRouter(prefix="/api/v1/applications", tags=["documents"])


async def _get_product_code(request: Request, session_id: str) -> str:
    stage = await _resolve_stage(request, session_id)
    if stage is None:
        raise HTTPException(404, "Unknown session")
    if stage == "discovery":
        raise HTTPException(409, "No product chosen yet — still in discovery")

    interview_graph = request.app.state.interview_graph
    snapshot = await interview_graph.aget_state(_interview_config(session_id))
    product_code = snapshot.values.get("product_code")
    if not product_code:
        raise HTTPException(500, "Session has no product on file")
    return product_code


@router.get("/{session_id}/documents/required")
async def list_required_documents(
    request: Request, session_id: str, db: AsyncSession = Depends(get_session)
):
    product_code = await _get_product_code(request, session_id)
    product = await core_banking.get_product(product_code)
    requirements = await core_banking.get_document_requirements(
        product["loan_type"], product["category"]
    )

    result = await db.execute(select(Document).where(Document.session_id == session_id))
    uploaded = {d.verification_type: d for d in result.scalars().all()}

    vr_result = await db.execute(select(VerificationResult).where(VerificationResult.session_id == session_id))
    verifications_by_doc: dict = {}
    for vr in vr_result.scalars().all():
        verifications_by_doc.setdefault(str(vr.document_id), []).append(vr.status)

    documents = []
    for doc_type in requirements["documents"]:
        existing = uploaded.get(doc_type["code"])
        statuses = verifications_by_doc.get(str(existing.id), []) if existing else []
        documents.append({
            "code": doc_type["code"],
            "name": doc_type["name"],
            "status": existing.status if existing else "not_uploaded",
            "document_id": str(existing.id) if existing else None,
            "verification": "mismatch" if "mismatch" in statuses else ("match" if statuses else None),
        })
    return {"session_id": session_id, "documents": documents}


@router.post("/{session_id}/documents", status_code=201)
async def upload_document(
    request: Request,
    session_id: str,
    verification_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
):
    product_code = await _get_product_code(request, session_id)
    product = await core_banking.get_product(product_code)
    requirements = await core_banking.get_document_requirements(
        product["loan_type"], product["category"]
    )
    valid_types = {d["code"] for d in requirements["documents"]}
    if verification_type not in valid_types:
        raise HTTPException(
            400,
            f"'{verification_type}' is not a required document for this application. "
            f"Valid types: {', '.join(sorted(valid_types))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty")

    content_type = file.content_type or "application/octet-stream"

    storage_path = await storage.save(session_id, file.filename or "upload", content)

    document = Document(
        id=uuid.uuid4(),
        session_id=session_id,
        verification_type=verification_type,
        original_filename=file.filename or "upload",
        storage_path=storage_path,
        content_type=file.content_type or "application/octet-stream",
        status="uploaded",
    )
    
    db.add(document)

    await db.flush()

    result = await extract_document(verification_type, content, content_type)

    if result["matches_claimed_type"]:
        document.status = "extracted"
        db.add(DocumentExtraction(
            document_id=document.id,
            extracted_fields=result["fields"],
            notes=result["notes"],
        ))

        interview_graph = request.app.state.interview_graph
        snapshot = await interview_graph.aget_state(_interview_config(session_id))
        filled = snapshot.values.get("filled") or {}

        verification_results = reconcile(verification_type, result["fields"], filled)
        for vr in verification_results:
            db.add(VerificationResult(
                session_id=session_id,
                slot_id=vr["slot_id"],
                document_id=document.id,
                declared_value=vr["declared_value"],
                extracted_value=vr["extracted_value"],
                status=vr["status"],
            ))
    else:
        document.status = "needs_reupload"

    await db.commit()
    await db.refresh(document)
  
    response = {
        "document_id": str(document.id),
        "verification_type": document.verification_type,
        "status": document.status,
        "uploaded_at": document.uploaded_at.isoformat(),
    }
    if document.status == "needs_reupload":
        response["reason"] = result["notes"] or "Document does not appear to match the required type."
    return response