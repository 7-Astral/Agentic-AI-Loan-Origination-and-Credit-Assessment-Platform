import asyncio
import base64
import json
import time
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.agents.assessment.retail import bank_analysis
from app.agents.document.categorize import categorize_transactions
from app.agents.document.pdf_text import render_pages
from app.agents.document.process import process_document
from app.agents.document.reconcile import RECONCILIATION_RULES, reconcile
from app.agents.document.sample_docs import SAMPLES, get_sample, load_layout, load_recording, sample_file
from app.agents.document.schemas import EXTRACTION_SCHEMAS
from app.api.playground import _metric_payload

router = APIRouter(prefix="/api/v1/playground/documents", tags=["playground"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_PREVIEW_PAGES = 8
PDF_PREVIEW_DPI = 110
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "application/pdf"}

DOCUMENT_TYPE_NAMES = {
    "primary_photo_id": "Photo ID",
    "proof_of_address": "Proof of address",
    "payslip_or_contract": "Payslip or employment contract",
    "payslip_or_tax_return": "Payslip or tax return",
    "bank_statements": "Bank statement",
    "tax_return": "Tax return",
    "loan_statement": "Loan statement",
    "contract_of_sale": "Contract of sale",
    "business_registration": "Business registration",
    "financial_statements": "Financial statement",
    "ato_position": "ATO position",
}

SLOT_LABELS = {
    "full_name": "Full name",
    "date_of_birth": "Date of birth (YYYY-MM-DD)",
    "current_address": "Current address",
    "employer_name": "Employer",
    "gross_annual_income": "Gross annual income",
    "vehicle_purchase_price": "Vehicle purchase price",
    "mortgage_balance": "Mortgage balance",
}


def _checks(code: str) -> list[dict]:
    return [
        {
            "slot_id": rule["slot_id"],
            "label": SLOT_LABELS.get(rule["slot_id"], rule["slot_id"]),
            "extracted_field": rule["extracted_field"],
            "compare": rule["compare"],
            "tolerance_pct": rule.get("tolerance_pct"),
        }
        for rule in RECONCILIATION_RULES.get(code, [])
    ]


def _document_types() -> list[dict]:
    return [
        {
            "code": code,
            "name": DOCUMENT_TYPE_NAMES.get(code, code),
            "fields": [{"id": field_id, "type": field_type} for field_id, field_type in schema.items()],
            "checks": _checks(code),
        }
        for code, schema in EXTRACTION_SCHEMAS.items()
    ]


def _statement_days(fields: dict) -> int | None:
    try:
        start = date.fromisoformat(str(fields.get("statement_period_start")))
        end = date.fromisoformat(str(fields.get("statement_period_end")))
    except ValueError:
        return None
    return (end - start).days + 1


def _model_error(exc: Exception) -> HTTPException:
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return HTTPException(
            429, "The AI model's request quota has been reached. Try again later, or use the recorded result."
        )
    if isinstance(exc, RuntimeError):
        return HTTPException(503, text)
    return HTTPException(502, f"The AI model call failed ({type(exc).__name__})")


@router.get("/options")
async def options():
    samples = []
    for sample in SAMPLES:
        recording = load_recording(sample)
        samples.append({
            "id": sample["id"],
            "label": sample["label"],
            "description": sample["description"],
            "verification_type": sample["verification_type"],
            "declared": sample["declared"],
            "mismatch_example": sample["mismatch_example"],
            "layout": load_layout(sample),
            "recording": (
                {"model": recording["model"], "recorded_at": recording["recorded_at"]} if recording else None
            ),
        })
    return {"samples": samples, "document_types": _document_types()}


def _is_pdf_sample(sample: dict) -> bool:
    return sample["filename"].lower().endswith(".pdf")


@router.get("/samples/{sample_id}/file")
async def sample_image(sample_id: str):
    sample = get_sample(sample_id)
    if sample is None:
        raise HTTPException(404, "Unknown sample")
    if _is_pdf_sample(sample):
        pages = await asyncio.to_thread(render_pages, sample_file(sample).read_bytes(), 1, PDF_PREVIEW_DPI)
        return Response(pages[0], media_type="image/png")
    return FileResponse(sample_file(sample), media_type="image/png")


def _borrow_categories(transactions: list[dict]) -> list[dict] | None:
    """The digital PDF sample holds the same transactions as the image sample, so it reuses the
    categories from that sample's recorded AI run instead of calling the model again."""
    donor = get_sample("bank_statement")
    recording = load_recording(donor) if donor else None
    if not recording:
        return None
    recorded = recording["result"]["fields"].get("transactions") or []
    lookup = {(t["date"], t["description"], t["amount"]): t.get("category") for t in recorded}
    categories = [lookup.get((t["date"], t["description"], t["amount"])) for t in transactions]
    if not transactions or any(c is None for c in categories):
        return None
    return [{**t, "category": c} for t, c in zip(transactions, categories)]


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


@router.post("/extract")
async def extract_document(
    verification_type: str = Form(...),
    declared: str = Form("{}"),
    sample_id: str | None = Form(None),
    live: bool = Form(False),
    categorize: bool = Form(True),
    file: UploadFile | None = File(None),
):
    if verification_type not in EXTRACTION_SCHEMAS:
        raise HTTPException(422, f"Unknown document type '{verification_type}'")
    try:
        declared_values = json.loads(declared)
    except ValueError:
        declared_values = None
    if not isinstance(declared_values, dict):
        raise HTTPException(422, "'declared' must be a JSON object")

    sample = get_sample(sample_id) if sample_id else None
    if sample_id and sample is None:
        raise HTTPException(404, "Unknown sample")

    started = time.perf_counter()
    recording_meta = None
    warnings: list[str] = []
    content: bytes | None = None
    recording = load_recording(sample) if sample and not live else None

    if sample and not live and recording is None and not _is_pdf_sample(sample):
        raise HTTPException(409, "No recording exists for this sample. Turn on live extraction.")
    if sample and verification_type != sample["verification_type"] and not live:
        raise HTTPException(
            409,
            "Recorded results only exist for the sample's own document type. "
            "Turn on live extraction to try another type.",
        )

    if recording is not None:
        result = dict(recording["result"])
        result["verifications"] = (
            reconcile(verification_type, result["fields"], declared_values) if result["matches_claimed_type"] else []
        )
        recording_meta = {"model": recording["model"], "recorded_at": recording["recorded_at"]}
    else:
        if sample:
            content = sample_file(sample).read_bytes()
            content_type = "application/pdf" if _is_pdf_sample(sample) else "image/png"
        elif file is not None:
            content_type = file.content_type or "application/octet-stream"
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise HTTPException(415, "Upload a PNG, JPEG, WebP or PDF file")
            content = await file.read()
            if not content:
                raise HTTPException(400, "Uploaded file is empty")
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "File is larger than 10 MB")
        else:
            raise HTTPException(422, "Provide a file or a sample_id")
        try:
            result = await process_document(verification_type, content, content_type, declared_values, categorize=False)
        except Exception as exc:
            raise _model_error(exc)

        transactions_read = result["fields"].get("transactions")
        if categorize and verification_type == "bank_statements" and result["matches_claimed_type"] and transactions_read:
            borrowed = _borrow_categories(transactions_read) if sample and _is_pdf_sample(sample) else None
            if borrowed:
                result["fields"]["transactions"] = borrowed
            else:
                try:
                    result["fields"]["transactions"] = await categorize_transactions(transactions_read)
                except Exception:
                    warnings.append(
                        "Spending categories could not be worked out because the AI model was unavailable or over its quota."
                    )

    fields = dict(result["fields"])
    transactions = fields.pop("transactions", None)
    schema = EXTRACTION_SCHEMAS[verification_type]
    checks = {c["slot_id"]: c for c in _checks(verification_type)}
    categorised = bool(transactions) and all(t.get("category") for t in transactions)

    impact = None
    if verification_type == "bank_statements" and transactions and categorised:
        impact = {
            "verified_expenses": _metric_payload(bank_analysis.verified_expenses(transactions)),
            "genuine_savings": _metric_payload(bank_analysis.genuine_savings(transactions)),
            "statement_days": _statement_days(fields),
        }

    pdf_pages = pdf_layout = None
    if result.get("method") == "pdf_text" and content is not None:
        images = await asyncio.to_thread(render_pages, content, PDF_PREVIEW_PAGES, PDF_PREVIEW_DPI)
        pdf_pages = [
            {"image": _data_url(png), "width": page["width"], "height": page["height"]}
            for png, page in zip(images, result["pages"])
        ]
        pdf_layout = {"fields": result["boxes"]["fields"], "rows": result["boxes"]["rows"]}

    return {
        "source": "recorded" if recording_meta else "live",
        "method": result.get("method", "ai_vision"),
        "recording": recording_meta,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "matches_claimed_type": result["matches_claimed_type"],
        "notes": result["notes"],
        "checks": result.get("checks"),
        "warnings": warnings,
        "fields": [
            {"id": field_id, "type": field_type, "value": fields.get(field_id)}
            for field_id, field_type in schema.items()
            if field_type != "transaction_list"
        ],
        "transactions": transactions,
        "verifications": [
            {
                **v,
                "compare": checks.get(v["slot_id"], {}).get("compare"),
                "tolerance_pct": checks.get(v["slot_id"], {}).get("tolerance_pct"),
            }
            for v in result["verifications"]
        ],
        "assessment_impact": impact,
        "pdf_pages": pdf_pages,
        "pdf_layout": pdf_layout,
    }
