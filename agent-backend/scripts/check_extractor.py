"""Test extraction against realistic applicant replies."""
import asyncio

import httpx

from app.agents.interaction.extractor import extract
from app.agents.interaction.resolver import next_batch
from app.agents.interaction.validation import ValidationError, validate

CASES = [
    ("straight answer", {}, "I need about 45 thousand over 5 years, paid fortnightly"),
    ("vague amount", {}, "Not sure exactly, somewhere around forty or fifty grand maybe"),
    ("mixed dump", {},
     "I want to borrow 500k for a house in Brunswick, I earn 120k before tax "
     "and I'm a full time operations manager at Telstra"),
    ("asks a question", {}, "What's the difference between fixed and variable?"),
    ("partial", {}, "45 thousand, not sure about the term yet"),
]


async def main():
    url = "http://127.0.0.1:9000/api/v1/products/HL-VAR-010/requirements"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            slots = resp.json()["slots"]
    except httpx.ConnectError:
        print("Cannot reach the mock bank on port 9000 — is uvicorn running?")
        return

    for name, filled, reply in CASES:
        batch = next_batch(slots, filled)
        result = await extract(batch, reply, slots)

        print(f"\n=== {name} ===")
        print(f"asked:  {', '.join(s['id'] for s in batch)}")
        print(f"reply:  {reply[:70]}")
        print(f"got:    {result['values']}")
        if result["unclear"]:
            print(f"unclear: {result['unclear']}")
        if result["notes"]:
            print(f"notes:  {result['notes']}")

        by_id = {s["id"]: s for s in slots}
        for slot_id, value in result["values"].items():
            if slot_id not in by_id:
                print(f"  ! unknown field {slot_id}")
                continue
            try:
                print(f"  ok {slot_id} -> {validate(by_id[slot_id], value)!r}")
            except ValidationError as exc:
                print(f"  ! {slot_id} rejected: {exc}")


if __name__ == "__main__":
    asyncio.run(main())