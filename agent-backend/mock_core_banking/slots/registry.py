from .business import BUSINESS_SLOTS
from .core import CORE_SLOTS
from .financial import FINANCIAL_SLOTS
from .overlays import HOME, INVESTMENT, OVERLAYS_BY_PRODUCT, VEHICLE

ALL_CORE_SLOTS = CORE_SLOTS + FINANCIAL_SLOTS

SCHEMA_VERSION = "2026.10-core-v7"

PRODUCT_OVERLAYS = OVERLAYS_BY_PRODUCT

CATEGORY_OVERLAYS = {
    ("personal", "vehicle"): VEHICLE,
    ("home", "owner_occupied"): HOME,
    ("home", "investment"): INVESTMENT,
}


def schema_for(product_code: str, loan_type: str | None = None, category: str | None = None) -> dict:
    """Return the versioned slot schema for one product."""
    code = product_code.upper()
    if loan_type == "business" or code.startswith("BL-"):
        slots = BUSINESS_SLOTS
    else:
        overlay = PRODUCT_OVERLAYS.get(code)
        if overlay is None:
            overlay = CATEGORY_OVERLAYS.get((loan_type, category), [])
        slots = ALL_CORE_SLOTS + overlay
    return {
        "product_code": code,
        "schema_version": SCHEMA_VERSION,
        "slot_count": len(slots),
        "slots": slots,
    }
