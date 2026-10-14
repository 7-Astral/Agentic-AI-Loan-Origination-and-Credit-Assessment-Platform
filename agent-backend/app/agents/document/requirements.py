from typing import Any

from app.agents.interaction.schema import is_required

DOCUMENT_CONDITIONS = {
    "entity_documents": "entity_structure in ('partnership', 'company', 'trust')",
}


DOCUMENT_ORDER = [
    "primary_photo_id", "proof_of_address", "business_registration", "entity_documents",
    "payslip_or_contract", "payslip_or_tax_return", "financial_statements", "tax_return",
    "ato_position", "bank_statements", "loan_statement", "contract_of_sale",
]


def order_key(document_code: str) -> int:
    return DOCUMENT_ORDER.index(document_code) if document_code in DOCUMENT_ORDER else len(DOCUMENT_ORDER)


def applies(document_code: str, filled: dict[str, Any]) -> bool:
    condition = DOCUMENT_CONDITIONS.get(document_code)
    if condition is None:
        return True
    return is_required({"id": document_code, "required_when": condition}, filled) is not False
