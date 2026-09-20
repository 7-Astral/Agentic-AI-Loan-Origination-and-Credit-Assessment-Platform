import random
import uuid
from datetime import date, datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .scenarios import SCENARIOS, band, identity_seed, pick_scenario

app = FastAPI(title="Mock Credit Bureau API", version="0.1.0")


class CreditReportRequest(BaseModel):
    full_name: str
    date_of_birth: date
    current_address: str | None = None
    consent: bool
    scenario: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/scenarios")
async def list_scenarios():
    return {"scenarios": [{"name": n, "description": d, "weight": w} for n, (d, _, w) in SCENARIOS.items()]}


@app.post("/api/v1/credit-report")
async def credit_report(payload: CreditReportRequest):
    if not payload.consent:
        raise HTTPException(403, "Consent to a credit check has not been recorded")
    if payload.scenario and payload.scenario not in SCENARIOS:
        raise HTTPException(422, f"Unknown scenario '{payload.scenario}'. Known: {sorted(SCENARIOS)}")

    seed = identity_seed(payload.full_name, payload.date_of_birth)
    scenario = payload.scenario or pick_scenario(seed)
    now = datetime.now(timezone.utc)
    file = SCENARIOS[scenario][1](random.Random(seed), now.date())
    score = file.pop("score")

    return {
        "report_id": f"MOCK-{uuid.uuid4().hex[:12].upper()}",
        "generated_at": now.isoformat(),
        "subject": {"full_name": payload.full_name, "date_of_birth": payload.date_of_birth.isoformat()},
        "score": {"value": score, "band": band(score), "scale_min": 0, "scale_max": 1200},
        **file,
        "mock": {"scenario": scenario},
    }
