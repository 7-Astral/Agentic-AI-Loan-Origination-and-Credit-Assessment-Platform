
import asyncio
import sys
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.assessment.demo_profiles import PRESETS
from app.agents.assessment.run import run_assessment
from app.agents.document.reconcile import reconcile
from app.agents.document.sample_docs import get_sample, load_recording, sample_file
from app.agents.interaction.graph import build_graph
from app.core.config import get_settings
from app.core.db import async_session
from app.core.identity import get_customer_id_from_token
from app.models.documents import Document, DocumentExtraction, VerificationResult
from app.services.core_banking import core_banking
from app.services.operational import (
    ensure_application,
    mirror_turn,
    record_platform_submission,
    set_application_product,
)

SEED_DOCUMENTS = ("payslip", "bank_statement")

# Preset loan types map onto the platform catalog's loan types.
CATALOG_LOAN_TYPE = {"personal": "personal", "vehicle": "personal", "home": "home"}


async def _customer_token(email: str, password: str) -> str:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.catalog_base_url.rstrip('/')}/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _attach_sample_documents(session_id: str, filled: dict) -> None:
    
    base = sample_file(get_sample(SEED_DOCUMENTS[0])).parents[4]
    async with async_session() as db:
        for sample_id in SEED_DOCUMENTS:
            sample = get_sample(sample_id)
            result = load_recording(sample)["result"]
            path = sample_file(sample)
            document = Document(
                id=uuid.uuid4(),
                application_id=uuid.UUID(session_id),
                verification_type=sample["verification_type"],
                original_filename=path.name,
                storage_path=path.relative_to(base).as_posix(),
                content_type="application/pdf" if path.suffix == ".pdf" else "image/png",
                status="extracted",
            )
            db.add(document)
            await db.flush()
            db.add(DocumentExtraction(document_id=document.id, extracted_fields=result["fields"], notes=result["notes"]))
            for vr in reconcile(sample["verification_type"], result["fields"], filled):
                db.add(VerificationResult(application_id=uuid.UUID(session_id), document_id=document.id, **vr))
        await db.commit()


async def main(preset_id: str, email: str, password: str) -> None:
    preset = next((p for p in PRESETS if p["id"] == preset_id), None)
    if preset is None:
        sys.exit(f"Unknown preset '{preset_id}'. Choose one of: {', '.join(p['id'] for p in PRESETS)}")

    reference = await core_banking.assessment.get_reference_product(preset["product_code"])
    loan_type = CATALOG_LOAN_TYPE.get(reference["loan_type"], reference["loan_type"])
    bank_id = await core_banking.resolve_default_bank_id()
    products = await core_banking.list_products(loan_type, bank_id=bank_id)
    filled = dict(preset["filled"])
    product = next(
        (
            p for p in products
            if p["min_amount"] <= filled["loan_amount"] <= p["max_amount"]
            and p["min_term_months"] <= filled["loan_term_months"] <= p["max_term_months"]
        ),
        None,
    )
    if product is None:
        sys.exit(
            f"No '{loan_type}' product in the platform catalog covers "
            f"${filled['loan_amount']:,} over {filled['loan_term_months']} months."
        )
    product_code = product["product_code"]

    applicant_id = get_customer_id_from_token(f"Bearer {await _customer_token(email, password)}")
    session_id = str(uuid.uuid4())
    await ensure_application(session_id, bank_id=bank_id, applicant_id=applicant_id)
    await set_application_product(session_id, product_code)

    schema = await core_banking.get_product_requirements(product_code, bank_id=bank_id)
    config = {"configurable": {"thread_id": f"{session_id}:interview"}}
    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.langgraph_db_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)
        await graph.aupdate_state(
            config,
            {
                "product_code": product_code,
                "schema_version": schema.get("schema_version"),
                "slots": schema["slots"],
                "filled": filled,
                "provenance": {key: {"source": "seed", "turn": 1} for key in filled},
                "transcript": [{
                    "role": "assistant",
                    "content": f"Seeded demo application: interview answers pre-filled from the "
                               f"'{preset_id}' playground preset ({preset['label']}).",
                }],
                "turn": 1,
                "current_batch": [],
            },
            as_node="finish",
        )
        values = (await graph.aget_state(config)).values
        await mirror_turn(session_id, values, complete=True)
        await _attach_sample_documents(session_id, filled)

        async with async_session() as db:
            assessment = await run_assessment(graph, config, db, session_id)

    result = await core_banking.catalog.submit_application(
        bank_id=bank_id,
        applicant_id=applicant_id,
        product_code=product_code,
        requested_amount=float(filled["loan_amount"]),
        tenure_requested_months=int(filled["loan_term_months"]),
        purpose=filled.get("purpose_detail") or filled.get("loan_purpose"),
        external_reference=session_id,
        applicant_legal_name=filled.get("full_name"),
        assessment_tier=(assessment.get("score_report") or {}).get("tier"),
        assessment_score=(assessment.get("score_report") or {}).get("overall_score"),
    )
    await record_platform_submission(session_id, result["application_id"], result["status"])

    score = assessment.get("score_report") or {}
    print(f"Session:              {session_id}")
    print(f"Product:              {product['name']} ({product_code})")
    print(f"Amount / term:        ${filled['loan_amount']:,} over {filled['loan_term_months']} months")
    print(f"5C tier / score:      {score.get('tier')} / {score.get('overall_score')}")
    print(f"Platform application: {result['application_id']} ({result['status']})")


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(
        args[0] if len(args) > 0 else "personal_strong",
        args[1] if len(args) > 1 else "customer@bank.com",
        args[2] if len(args) > 2 else "Customer@123",
    ))
