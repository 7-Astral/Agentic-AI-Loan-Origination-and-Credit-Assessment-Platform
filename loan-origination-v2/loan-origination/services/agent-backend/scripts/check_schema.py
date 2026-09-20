"""Verify the slot schema and conditional-requirement logic."""
import asyncio
from collections import Counter

import httpx

from app.agents.interaction.schema import is_required, unfilled_required


async def main():
    url = "http://127.0.0.1:9000/api/v1/products/PL-STD-001/requirements"
    async with httpx.AsyncClient(timeout=10) as client:
        schema = (await client.get(url)).json()

    slots = schema["slots"]
    print(f"version {schema['schema_version']}  product {schema['product_code']}")
    print(f"{schema['slot_count']} slots")
    print("by phase:", dict(sorted(Counter(s["phase"] for s in slots).items())))

    print("\nconditional slots:")
    for s in slots:
        if s["required_when"]:
            print(f"  {s['id']:<24} when {s['required_when']}")

    print("\nempty state -> unconditional slots only")
    print(f"  {len(unfilled_required(slots, {}))} slots to ask")

    filled = {"residency_status": "temporary_visa", "years_at_address": 1,
              "employment_status": "full_time", "months_in_current_role": 3}
    print("\nafter answering 4 slots, conditionals resolve:")
    for sid in ["visa_subclass", "previous_address", "employer_name",
                "on_probation", "abn_years_trading"]:
        s = next(x for x in slots if x["id"] == sid)
        print(f"  {sid:<24} required={is_required(s, filled)}")


if __name__ == "__main__":
    asyncio.run(main()) 