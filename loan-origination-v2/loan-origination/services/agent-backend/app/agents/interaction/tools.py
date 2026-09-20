from typing import Literal

from langchain_core.tools import tool

from app.services.core_banking import core_banking

LoanType = Literal["personal", "home", "business"]

TYPE_ALIASES = {
    "mortgage": "home", "house": "home", "property": "home",
    "sme": "business", "commercial": "business",
}

VALID_TYPES = {"personal", "home", "business"}


def normalise_loan_type(value: str) -> str | None:
    if not value:
        return None
    key = value.strip().lower().replace(" ", "_").replace("-", "_")
    if key in VALID_TYPES:
        return key
    return TYPE_ALIASES.get(key)


def _format_product(p: dict) -> str:
    security = "secured" if p.get("secured") else "unsecured"
    return (
        f"{p['product_code']} | {p['name']} | "
        f"${p['min_amount']:,}-${p['max_amount']:,} | "
        f"{p['min_term_months']}-{p['max_term_months']} months | "
        f"{p['interest_rate']}% {p['rate_type']} | {security}"
    )


@tool
async def list_loan_types() -> str:
    types = await core_banking.list_loan_types()
    lines = []
    for t in types:
        subtypes = ", ".join(c["name"] for c in t.get("categories", []))
        lines.append(f"{t['code']}: {t['name']} — {t['description']} (subtypes: {subtypes})")
    return "\n".join(lines)


@tool
async def list_products(loan_type: LoanType, category: str | None = None) -> str:
    canonical = normalise_loan_type(loan_type)
    if canonical is None:
        return (
            f"'{loan_type}' is not a loan type this lender offers. "
            f"Valid types: {', '.join(sorted(VALID_TYPES))}. "
            "Call list_loan_types if unsure."
        )

    try:
        products = await core_banking.list_products(canonical, category)
    except Exception:
        suffix = f"/{category}" if category else ""
        return f"No products currently available for {canonical}{suffix}."

    if not products:
        return f"No products currently available for {canonical} loans."

    lines = [_format_product(p) for p in products]
    return f"Products for {canonical} loans:\n" + "\n".join(lines)


INTERACTION_TOOLS = [list_loan_types, list_products]