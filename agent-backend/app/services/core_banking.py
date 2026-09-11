import httpx

from app.core.config import get_settings

DEFAULT_BANK_ID = "default"


class CoreBankingClient:
    def __init__(self) -> None:
        s = get_settings()
        self._base_url = s.core_banking_base_url.rstrip("/")
        self._timeout = s.core_banking_timeout
        self._headers = {"X-API-Key": s.core_banking_api_key}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def list_loan_types(self, bank_id: str = DEFAULT_BANK_ID) -> list[dict]:
        data = await self._get("/api/v1/loan-types", params={"bank_id": bank_id})
        return data["loan_types"]

    async def list_products(
        self, loan_type: str | None = None, category: str | None = None, bank_id: str = DEFAULT_BANK_ID
    ) -> list[dict]:
        params = {"bank_id": bank_id}
        if loan_type:
            params["loan_type"] = loan_type
        if category:
            params["category"] = category
        data = await self._get("/api/v1/products", params=params)
        return data["products"]

    async def get_product(self, product_code: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self._get(f"/api/v1/products/{product_code}", params={"bank_id": bank_id})

    async def get_product_requirements(self, product_code: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self._get(
            f"/api/v1/products/{product_code}/requirements", params={"bank_id": bank_id}
        )

    async def get_document_requirements(
        self, loan_type: str, category: str, bank_id: str = DEFAULT_BANK_ID
    ) -> dict:
        return await self._get(
            f"/api/v1/loan-types/{loan_type}/categories/{category}/document-requirements",
            params={"bank_id": bank_id},
        )

    async def get_policy(self, key: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self._get(f"/api/v1/policy/{key}", params={"bank_id": bank_id})

    async def get_rules(self, framework: str, bank_id: str = DEFAULT_BANK_ID) -> list[dict]:
        data = await self._get("/api/v1/rules", params={"framework": framework, "bank_id": bank_id})
        return data["rules"]
core_banking = CoreBankingClient()