import asyncio

from sqlalchemy import select

from mock_core_banking.db import async_session, engine
from mock_core_banking.models import Base, DocumentRequirement, DocumentType
from mock_core_banking.seed import DEFAULT_BANK_ID, DOCUMENT_REQUIREMENTS, DOCUMENT_TYPES


async def seed_documents():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        existing_types = set((await session.execute(
            select(DocumentType.code).where(DocumentType.bank_id == DEFAULT_BANK_ID)
        )).scalars())
        new_types = [dt for dt in DOCUMENT_TYPES if dt["code"] not in existing_types]
        for dt in new_types:
            session.add(DocumentType(bank_id=DEFAULT_BANK_ID, **dt))
        await session.flush()

        existing_reqs = set((await session.execute(
            select(
                DocumentRequirement.loan_type_code,
                DocumentRequirement.category_code,
                DocumentRequirement.document_type_code,
            ).where(DocumentRequirement.bank_id == DEFAULT_BANK_ID)
        )).all())
        new_reqs = [
            dr for dr in DOCUMENT_REQUIREMENTS
            if (dr["loan_type_code"], dr["category_code"], dr["document_type_code"]) not in existing_reqs
        ]
        for dr in new_reqs:
            session.add(DocumentRequirement(bank_id=DEFAULT_BANK_ID, **dr))
        await session.commit()

    print(f"Document types added: {len(new_types)}. Requirements added: {len(new_reqs)}.")


if __name__ == "__main__":
    asyncio.run(seed_documents())
