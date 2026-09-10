from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mock_core_banking.db import get_session
from mock_core_banking.models import DocumentRequirement, DocumentType
from mock_core_banking.routers.deps import get_bank_or_404
from mock_core_banking.schemas import DocumentTypeCreate, DocumentTypeOut, DocumentRequirementToggle

router = APIRouter(prefix="/api/v1/banks/{bank_id}", tags=["admin:documents"])


@router.get("/document-types", response_model=list[DocumentTypeOut])
async def list_document_types(bank_id: str, session: AsyncSession = Depends(get_session)):
    await get_bank_or_404(bank_id, session)
    result = await session.execute(select(DocumentType).where(DocumentType.bank_id == bank_id))
    return list(result.scalars().all())


@router.post("/document-types", response_model=DocumentTypeOut, status_code=201)
async def create_document_type(
    bank_id: str, payload: DocumentTypeCreate, session: AsyncSession = Depends(get_session)
):
    await get_bank_or_404(bank_id, session)
    existing = await session.get(DocumentType, {"bank_id": bank_id, "code": payload.code})
    if existing is not None:
        raise HTTPException(409, f"Document type '{payload.code}' already exists for this bank")
    doc_type = DocumentType(bank_id=bank_id, code=payload.code, name=payload.name)
    session.add(doc_type)
    await session.commit()
    return doc_type


@router.post("/document-requirements/toggle", status_code=200)
async def toggle_document_requirement(
    bank_id: str,
    payload: DocumentRequirementToggle,
    session: AsyncSession = Depends(get_session),
):
    await get_bank_or_404(bank_id, session)

    result = await session.execute(
        select(DocumentRequirement).where(
            DocumentRequirement.bank_id == bank_id,
            DocumentRequirement.loan_type_code == payload.loan_type_code,
            DocumentRequirement.category_code == payload.category_code,
            DocumentRequirement.document_type_code == payload.document_type_code,
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        await session.commit()
        return {"active": False}

    req = DocumentRequirement(
        bank_id=bank_id,
        loan_type_code=payload.loan_type_code,
        category_code=payload.category_code,
        document_type_code=payload.document_type_code,
    )
    session.add(req)
    await session.commit()
    return {"active": True}
