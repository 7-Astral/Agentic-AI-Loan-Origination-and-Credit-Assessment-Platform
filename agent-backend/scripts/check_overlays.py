"""Compare slot schemas across all products."""
import asyncio
from collections import Counter

import httpx

from app.agents.interaction.schema import unfilled_required

PRODUCTS = ["PL-STD-001", "PL-SEC-002", "HL-VAR-010", "VL-NEW-020",
            "BL-TERM-030", "IL-PROP-040"]


async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            schemas = {}
            for code in PRODUCTS:
                resp = await client.get(
                    f"http://127.0.0.1:9000/api/v1/products/{code}/requirements"
                )
                resp.raise_for_status()
                schemas[code] = resp.json()
        except httpx.ConnectError:
            print("Cannot reach the mock bank on port 9000 — is uvicorn running?")
            return

    print(f"{'product':<14}{'total':>7}{'overlay':>9}{'to ask':>8}   phases")
    for code, schema in schemas.items():
        slots = schema["slots"]
        overlay = [s for s in slots if s["phase"] == 5]
        phases = sorted(Counter(s["phase"] for s in slots))
        print(
            f"{code:<14}{schema['slot_count']:>7}{len(overlay):>9}"
            f"{len(unfilled_required(slots, {})):>8}   {phases}"
        )

    print("\nvehicle overlay:")
    for s in schemas["VL-NEW-020"]["slots"]:
        if s["phase"] == 5:
            cond = f"  when {s['required_when']}" if s["required_when"] else ""
            print(f"  {s['id']:<32}{s['type']:<10}{cond}")

    print("\nballoon conditional:")
    home = schemas["HL-VAR-010"]["slots"]
    fhb = [s["id"] for s in home
           if s["required_when"] and "first_home_buyer" in s["required_when"]]
    print(f"  home loan slots gated on first_home_buyer: {fhb}")


if __name__ == "__main__":
    asyncio.run(main())