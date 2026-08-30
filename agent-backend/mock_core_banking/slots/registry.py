from .core import CORE_SLOTS
from .financial import FINANCIAL_SLOTS
from .overlays import OVERLAYS_BY_PRODUCT

ALL_CORE_SLOTS = CORE_SLOTS + FINANCIAL_SLOTS

SCHEMA_VERSION = "2026.08-core-v3"

PRODUCT_OVERLAYS = OVERLAYS_BY_PRODUCT

def schema_for(product_code: str) -> dict:
    """Return the versioned slot schema for one product."""
    overlay = PRODUCT_OVERLAYS.get(product_code.upper(), [])
    slots = ALL_CORE_SLOTS + overlay
    return {
        "product_code": product_code.upper(),
        "schema_version": SCHEMA_VERSION,
        "slot_count": len(slots),
        "slots": slots,
    }