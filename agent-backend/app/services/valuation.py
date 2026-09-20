import httpx

from app.core.config import get_settings

DOMAIN_API_BASE = "https://api.domain.com.au/v1"


async def find_property_id(address: str) -> str | None:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DOMAIN_API_BASE}/properties/_suggest",
            params={"terms": address, "channel": "All"},
            headers={"X-API-Key": settings.domain_api_key},
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        return None
    return results[0]["id"]


async def get_price_estimate(property_id: str) -> dict | None:
    """Confirmed against Domain's real docs — returns
    {'low', 'mid', 'high', 'confidence', 'date'} or None."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DOMAIN_API_BASE}/properties/{property_id}/priceEstimate",
            headers={"X-API-Key": settings.domain_api_key},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

    if "midPrice" not in data:
        return None

    return {
        "low": data.get("lowerPrice"),
        "mid": data.get("midPrice"),
        "high": data.get("upperPrice"),
        "confidence": data.get("priceConfidence"),
        "date": data.get("date"),
    }


async def get_rental_estimate(property_id: str) -> dict | None:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DOMAIN_API_BASE}/properties/{property_id}/rentalEstimate",
            headers={"X-API-Key": settings.domain_api_key},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

    return {
        "low": data.get("lowerRent"),
        "mid": data.get("midRent"),
        "high": data.get("upperRent"),
        "confidence": data.get("rentConfidence"),
        "date": data.get("date"),
        "_raw": data,
    }


async def get_property_estimate(address: str) -> dict | None:
    property_id = await find_property_id(address)
    if property_id is None:
        return None
    return await get_price_estimate(property_id)


async def get_rental_appraisal(address: str) -> dict | None:
    property_id = await find_property_id(address)
    if property_id is None:
        return None
    return await get_rental_estimate(property_id)