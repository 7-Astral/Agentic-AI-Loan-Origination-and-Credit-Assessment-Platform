import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"

SAMPLES = [
    {
        "id": "payslip", "label": "Payslip",
        "description": "Fortnightly payslip for a full-time employee.",
        "verification_type": "payslip_or_contract", "filename": "payslip.png",
        "declared": {"employer_name": "Harbourview Logistics"},
        "mismatch_example": {"employer_name": "Acme Mining Pty Ltd"},
    },
    {
        "id": "bank_statement", "label": "Bank statement",
        "description": "One month of transactions, including a $9,000 gift from a relative.",
        "verification_type": "bank_statements", "filename": "bank_statement.png",
        "declared": {"full_name": "Jane Citizen"},
        "mismatch_example": {"full_name": "Robert Nguyen"},
    },
    {
        "id": "bank_statement_pdf", "label": "Bank statement (digital PDF)",
        "description": "The same statement as a PDF with selectable text. Read directly, no AI needed.",
        "verification_type": "bank_statements", "filename": "bank_statement.pdf",
        "declared": {"full_name": "Jane Citizen"},
        "mismatch_example": {"full_name": "Robert Nguyen"},
    },
    {
        "id": "utility_bill", "label": "Utility bill (proof of address)",
        "description": "Quarterly electricity and gas bill.",
        "verification_type": "proof_of_address", "filename": "utility_bill.png",
        "declared": {"current_address": "12 Wattle St, Brunswick VIC 3056"},
        "mismatch_example": {"current_address": "88 Ocean Road, Torquay VIC 3228"},
    },
]


def get_sample(sample_id: str) -> dict | None:
    return next((s for s in SAMPLES if s["id"] == sample_id), None)


def sample_file(sample: dict) -> Path:
    return SAMPLES_DIR / sample["filename"]


def recording_file(sample: dict) -> Path:
    return SAMPLES_DIR / f"{sample['id']}.recorded.json"


def load_layout(sample: dict) -> dict | None:
    """Where each value is printed on the sample page, in CSS pixels. See scripts/make_sample_documents.py."""
    path = SAMPLES_DIR / f"{sample['id']}.boxes.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_recording(sample: dict) -> dict | None:
    path = recording_file(sample)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
