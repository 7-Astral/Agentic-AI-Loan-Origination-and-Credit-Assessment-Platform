"""Dry-run the resolver with scripted answers — no LLM involved."""
import asyncio

import httpx

from app.agents.interaction.resolver import commit, next_batch, progress
from app.agents.interaction.validation import ValidationError, validate

PRODUCT = "VL-NEW-020"

ANSWERS = {
    "loan_amount": "45k", "loan_term_months": 60,
    "repayment_frequency": "fortnightly", "loan_purpose": "purchase_vehicle",
    "purpose_detail": "Replacing an old car that keeps breaking down",
    "full_name": "Jordan Alex Reyes", "date_of_birth": "1994-03-12",
    "mobile_number": "0412345678", "email_address": "jordan@example.com",
    "residency_status": "citizen", "tax_resident_au": "yes",
    "marital_status": "de_facto", "dependants": 1,
    "living_arrangement": "renting",
    "current_address": "12 Example St, Brunswick VIC 3056",
    "years_at_address": 5,
    "employment_status": "full_time", "employer_name": "Acme Logistics",
    "job_title": "Operations coordinator", "months_in_current_role": 30,
    "gross_annual_income": "95,000", "net_income_amount": 2900,
    "net_income_frequency": "monthly",
    "savings_balance": 18000, "owns_property": "no",
    "credit_card_limit_total": 6000, "credit_card_balance_total": 1200,
    "other_loan_repayments_monthly": 0,
    "has_hecs_help": "yes", "hecs_help_balance": 22000,
    "exp_food_groceries": 700, "exp_clothing_personal_care": 120,
    "exp_recreation_holidays": 250, "exp_education_childcare": 400,
    "exp_insurance": 180, "exp_medical_health": 90,
    "exp_rent_board": 1400, "exp_other_housing": 200,
    "exp_phone_internet_media": 110, "exp_vehicle_transport": 320,
    "vehicle_condition": "new", "vehicle_make_model": "Toyota Corolla Hybrid",
    "vehicle_year": 2026, "vehicle_purchase_price": 42000,
    "seller_type": "dealer", "trade_in_or_deposit": 3000,
    "wants_balloon": "no",
    "credit_check_consent": "yes", "privacy_acknowledged": "yes",
    "summary_confirmed": "yes",
}


async def main():
    url = f"http://127.0.0.1:9000/api/v1/products/{PRODUCT}/requirements"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            schema = resp.json()
    except httpx.ConnectError:
        print("Cannot reach the mock bank on port 9000 — is uvicorn running?")
        return

    slots = schema["slots"]
    filled: dict = {}
    provenance: dict = {}
    turn = 0

    print(f"{PRODUCT}  schema {schema['schema_version']}  {len(slots)} slots\n")

    while True:
        batch = next_batch(slots, filled)
        if not batch:
            break
        turn += 1
        ids = ", ".join(s["id"] for s in batch)
        print(f"turn {turn:>2}  phase {batch[0]['phase']}  "
              f"{batch[0]['group'] or '-':<13} [{len(batch)}] {ids}")

        for s in batch:
            if s["id"] not in ANSWERS:
                print(f"\n  no scripted answer for {s['id']} — stopping")
                return
            try:
                value = validate(s, ANSWERS[s["id"]])
            except ValidationError as exc:
                print(f"\n  {s['id']} rejected: {exc}")
                return
            commit(filled, provenance, s["id"], value, "asked", turn)

        if turn > 40:
            print("  loop guard tripped")
            return

    p = progress(slots, filled)
    print(f"\ncomplete in {turn} turns — {p['answered']} slots filled")
    print(f"skipped by conditions: {len(slots) - p['answered']}")
    print("\nnormalisation samples:")
    for key in ["loan_amount", "gross_annual_income", "tax_resident_au",
                "date_of_birth", "owns_property"]:
        print(f"  {key:<24}{ANSWERS[key]!r:<40} -> {filled[key]!r}")


if __name__ == "__main__":
    asyncio.run(main())