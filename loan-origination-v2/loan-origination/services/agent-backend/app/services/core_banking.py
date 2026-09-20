"""Two backends behind one familiar interface.

- CatalogClient talks to the main platform's services/api: the source of
  truth for banks/loan_products/lending_policies (product catalog).
- AssessmentConfigClient talks to mock_core_banking: document checklists,
  HEM/shading policy, Five C's rules, and interview slot schemas — bank
  assessment configuration, not staff-managed catalog data.

`core_banking` below is the same object call sites already import; only its
insides changed, so interview.py / documents.py / assessment/run.py did not
need to change their call sites for the catalog-facing methods.
"""

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
    """Product catalog — services/api."""

    def __init__(self) -> None:
        s = get_settings()
        super().__init__(s.catalog_base_url, s.catalog_api_key, s.catalog_timeout)
        self._configured_bank_id = s.platform_bank_id or None
        self._bank_code = s.platform_bank_code
        self._resolved_bank_id: str | None = None

    async def _default_bank_id_async(self) -> str:
        """Resolves the platform's default bank id. Prefers an explicit
        platform_bank_id if one is configured; otherwise looks it up by the
        stable bank code (set once, in seed.py) so this never goes stale
        when the database is wiped and reseeded with fresh random ids."""
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
    ) -> dict:
        """Hands a completed interview into the platform's real loan
        pipeline (loan_applications + route_loan_decision)."""
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
            },
        )


class AssessmentConfigClient(_BaseClient):
    """Document checklists, policy, rules, interview slot schemas — mock_core_banking."""

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


class CoreBankingClient:
    """Facade kept for source-compatibility with existing call sites."""

    def __init__(self) -> None:
        self.catalog = CatalogClient()
        self.assessment = AssessmentConfigClient()

    # -- catalog --------------------------------------------------------
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
        """Resolves the platform's default bank id the same way catalog calls
        already do — an explicit platform_bank_id if configured, otherwise by
        the stable bank code (see CatalogClient._default_bank_id_async).
        Needed wherever a bank id has to be known before any catalog call can
        happen, e.g. starting a brand-new chat session."""
        return await self.catalog._default_bank_id_async()

    async def get_product_requirements(self, product_code: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        """Interview slot schema for a product. Looks the product up in the
        catalog first (to learn its assessment-config loan_type), then asks
        mock_core_banking for the static slot schema under that loan_type —
        the product itself never needs to exist in mock_core_banking's DB."""
        product = await self.get_product(product_code, bank_id=bank_id)
        return await self.assessment.get_interview_schema(product_code, loan_type=product["loan_type"])

    # -- assessment configuration ----------------------------------------
    async def get_document_requirements(
        self, loan_type: str, category: str, bank_id: str = DEFAULT_BANK_ID
    ) -> dict:
        return await self.assessment.get_document_requirements(loan_type, category, bank_id=DEFAULT_BANK_ID)

    async def get_policy(self, key: str, bank_id: str = DEFAULT_BANK_ID) -> dict:
        return await self.assessment.get_policy(key, bank_id=DEFAULT_BANK_ID)

    async def get_rules(self, framework: str, bank_id: str = DEFAULT_BANK_ID) -> list[dict]:
        return await self.assessment.get_rules(framework, bank_id=DEFAULT_BANK_ID)


core_banking = CoreBankingClient()
