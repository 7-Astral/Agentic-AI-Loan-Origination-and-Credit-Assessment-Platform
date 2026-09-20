"""Check question phrasing across batch types."""
import asyncio

import httpx

from app.agents.interaction.questioner import ask
from app.agents.interaction.resolver import next_batch

SCENARIOS = [
    ("opening", {}, [], False, None),
    ("intrusive — dependants",
     {"loan_amount": 45000, "loan_term_months": 60, "repayment_frequency": "monthly",
      "loan_purpose": "purchase_vehicle", "purpose_detail": "old car dying",
      "full_name": "Jordan Reyes", "date_of_birth": "1994-03-12",
      "mobile_number": "0412345678", "email_address": "j@example.com",
      "residency_status": "citizen", "tax_resident_au": True},
     [], False, None),
    ("ten expenses at once",
     {"loan_amount": 45000, "loan_term_months": 60, "repayment_frequency": "monthly",
      "loan_purpose": "purchase_vehicle", "purpose_detail": "old car dying",
      "full_name": "Jordan Reyes", "date_of_birth": "1994-03-12",
      "mobile_number": "0412345678", "email_address": "j@example.com",
      "residency_status": "citizen", "tax_resident_au": True,
      "marital_status": "de_facto", "dependants": 1,
      "living_arrangement": "renting", "current_address": "12 Example St, Brunswick VIC",
      "years_at_address": 5, "employment_status": "full_time",
      "employer_name": "Acme", "job_title": "Coordinator",
      "months_in_current_role": 30, "gross_annual_income": 95000,
      "net_income_amount": 2900, "net_income_frequency": "monthly",
      "savings_balance": 18000, "owns_property": False,
      "credit_card_limit_total": 0, "other_loan_repayments_monthly": 0,
      "has_hecs_help": False},
     [], False, None),
    ("repair after bad address",
     {"loan_amount": 45000, "loan_term_months": 60, "repayment_frequency": "monthly",
      "loan_purpose": "purchase_vehicle", "purpose_detail": "old car dying",
      "full_name": "Jordan Reyes", "date_of_birth": "1994-03-12",
      "mobile_number": "0412345678", "email_address": "j@example.com",
      "residency_status": "citizen", "tax_resident_au": True,
      "marital_status": "single", "dependants": 0, "living_arrangement": "renting"},
     [{"role": "assistant", "content": "What's your current address?"},
      {"role": "user", "content": "Brunswick"}],
     True, "needs a full street address including the street number"),
    ("applicant asked a question",
     {"loan_amount": 45000},
     [{"role": "assistant", "content": "How long would you like to repay it over?"},
      {"role": "user", "content": "What's the difference between fixed and variable?"}],
     False, None),
]


async def main():
    url = "http://127.0.0.1:9000/api/v1/products/VL-NEW-020/requirements"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            slots = resp.json()["slots"]
    except httpx.ConnectError:
        print("Cannot reach the mock bank on port 9000 — is uvicorn running?")
        return

    for name, filled, history, repair, error in SCENARIOS:
        batch = next_batch(slots, filled)
        if not batch:
            print(f"\n=== {name} ===\n  nothing left to ask")
            continue
        question = await ask(batch, filled, history, repair, error)
        print(f"\n=== {name} ===")
        print(f"asking: {', '.join(s['id'] for s in batch)}")
        print(f"\n{question}\n")


if __name__ == "__main__":
    asyncio.run(main())