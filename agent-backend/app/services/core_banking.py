import httpx

from app.core.config import get_settings

DEFAULT_BANK_ID = "default"


class _BaseClient:
    def __init__(self, base_url: str, api_key: str, timeout: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._headers = {"X-API-Key": api_key}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, json: dict) -> dict:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=json, headers=self._headers)
            resp.raise_for_status()
            return resp.json()


class CatalogClient(_BaseClient):

    def __init__(self) -> None:
        s = get_settings()
        super().__init__(s.catalog_base_url, s.catalog_api_key, s.catalog_timeout)
        self._configured_bank_id = s.platform_bank_id or None
        self._bank_code = s.platform_bank_code
        self._resolved_bank_id: str | None = None

    async def _default_bank_id_async(self) -> str:

        if self._configured_bank_id:
            return self._configured_bank_id
        if not self._resolved_bank_id:
            data = await self._get(f"/api/v1/banks/by-code/{self._bank_code}")
            self._resolved_bank_id = data["id"]
        return self._resolved_bank_id

    async def list_loan_types(self, bank_id: str | None = None) -> list[dict]:
        resolved = bank_id or await self._default_bank_id_async()
        data = await self._get("/api/v1/loan-types", params={"bank_id": resolved})
        return data["loan_types"]

    async def list_products(
        self, loan_type: str | None = None, category: str | None = None, bank_id: str | None = None
    ) -> list[dict]:
        resolved = bank_id or await self._default_bank_id_async()
        params = {"bank_id": resolved}
        if loan_type:
            params["loan_type"] = loan_type
        if category:
            params["category"] = category
        data = await self._get("/api/v1/products", params=params)
        return data["products"]

    async def get_product(self, product_code: str, bank_id: str | None = None) -> dict:
        resolved = bank_id or await self._default_bank_id_async()
        return await self._get(f"/api/v1/products/{product_code}", params={"bank_id": resolved})

    async def submit_application(
        self,
        *,
        bank_id: str,
        applicant_id: str,
        product_code: str,
        requested_amount: float,
        tenure_requested_months: int,
        purpose: str | None,
        external_reference: str | None,
        applicant_legal_name: str | None = None,
        assessment_tier: str | None = None,
        assessment_score: float | None = None,
    ) -> dict:
       
        return await self._post(
            "/api/v1/applications",
            json={
                "bank_id": bank_id,
                "applicant_id": applicant_id,
                "product_code": product_code,
                "requested_amount": requested_amount,
                "tenure_requested_months": tenure_requested_months,
                "purpose": purpose,
                "external_reference": external_reference,
                "applicant_legal_name": applicant_legal_name,
                "assessment_tier": assessment_tier,
                "assessment_score": assessment_score,
            },
        )


class AssessmentConfigClient(_BaseClient):

    def __init__(self) -> None:
        s = get_settings()
        super().__init__(s.core_banking_base_url, s.core_banking_api_key, s.core_banking_timeout)

    async def get_interview_schema(self, product_code: str, loan_type: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self._get(
            f"/api/v1/interview-schema/{product_code}",
            params={"loan_type": loan_type, "bank_id": bank_id},
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

   
    async def list_reference_products(self, bank_id: str = DEFAULT_BANK_ID) -> list[dict]:
        data = await self._get("/api/v1/products", params={"bank_id": bank_id})
        return data["products"]

    async def get_reference_product(self, product_code: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self._get(f"/api/v1/products/{product_code}", params={"bank_id": bank_id})


class CoreBankingClient:

    def __init__(self) -> None:
        self.catalog = CatalogClient()
        self.assessment = AssessmentConfigClient()

    async def list_loan_types(self, bank_id: str = DEFAULT_BANK_ID) -> list[dict]:
        return await self.catalog.list_loan_types(bank_id=None if bank_id == DEFAULT_BANK_ID else bank_id)

    async def list_products(
        self, loan_type: str | None = None, category: str | None = None, bank_id: str = DEFAULT_BANK_ID
    ) -> list[dict]:
        return await self.catalog.list_products(
            loan_type=loan_type, category=category, bank_id=None if bank_id == DEFAULT_BANK_ID else bank_id
        )

    async def get_product(self, product_code: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self.catalog.get_product(product_code, bank_id=None if bank_id == DEFAULT_BANK_ID else bank_id)

    async def resolve_default_bank_id(self) -> str:
       
        return await self.catalog._default_bank_id_async()

    async def get_product_requirements(self, product_code: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
       
        product = await self.get_product(product_code, bank_id=bank_id)
        return await self.assessment.get_interview_schema(product_code, loan_type=product["loan_type"])

    async def get_document_requirements(
        self, loan_type: str, category: str, bank_id: str = DEFAULT_BANK_ID
    ) -> dict:
        return await self.assessment.get_document_requirements(loan_type, category, bank_id=DEFAULT_BANK_ID)

    async def get_policy(self, key: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self.assessment.get_policy(key, bank_id=DEFAULT_BANK_ID)

    async def get_rules(self, framework: str, bank_id: str = DEFAULT_BANK_ID) -> list[dict]:
        return await self.assessment.get_rules(framework, bank_id=DEFAULT_BANK_ID)


core_banking = CoreBankingClient()
