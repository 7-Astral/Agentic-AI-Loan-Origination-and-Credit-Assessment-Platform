import argparse
import asyncio

from app.agents.assessment.demo_profiles import PRESETS, SAMPLE_STATEMENT
from app.agents.assessment.run import compute_assessment
from app.services.bureau import get_credit_report
from app.services.core_banking import DEFAULT_BANK_ID

KEY_METRICS = [
    "shaded_income", "assessed_living_expenses", "proposed_repayment", "monthly_surplus", "nsr", "dti",
    "deposit_amount", "contribution_pct", "net_asset_position", "genuine_savings",
    "credit_score", "worst_rhi_24mo", "enquiry_velocity_6mo", "undisclosed_liabilities",
]


def _show(value) -> str:
    return "-" if value is None else str(value)


async def run_preset(preset: dict, full: bool) -> None:
    filled = preset["filled"]
    bureau_report = await get_credit_report(filled, preset["bureau_scenario"])
    result = await compute_assessment(
        filled, preset["product_code"], bank_id=DEFAULT_BANK_ID,
        bank_transactions=SAMPLE_STATEMENT if preset["use_sample_statement"] else None,
        bureau_report=bureau_report,
    )
    metrics, verdict = result["metrics"], result["route"]
    computed = sum(1 for m in metrics.values() if m.usable)

    bureau = bureau_report["mock"]["scenario"] if bureau_report else "none"
    print(f"\n=== {preset['id']}  [{preset['product_code']}, bureau: {bureau}]")
    print(f"    metrics {computed}/{len(metrics)} computed  ->  {verdict['tier']}  "
          f"(fail {verdict['fail_count']}, flag {verdict['flag_count']}, provisional {verdict['provisional_count']})")

    shown = metrics if full else {k: metrics[k] for k in KEY_METRICS}
    for name, m in shown.items():
        print(f"      {name:28} {m.state.value:14} {_show(m.value)}")

    for r in result["rule_results"]:
        if r["status"] in ("fail", "flag"):
            print(f"    ! {r['status']:5} {r['rule_id']:34} {r.get('message', '')}")
        elif r["status"] == "provisional":
            print(f"    ? prov  {r['rule_id']:34} missing: {', '.join(r['missing'])}")
        else:
            print(f"    x {r['status']:5} {r['rule_id']:34} {r.get('detail', '')}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=[p["id"] for p in PRESETS])
    parser.add_argument("--full", action="store_true", help="print every metric")
    args = parser.parse_args()

    for preset in PRESETS:
        if args.profile in (None, preset["id"]):
            await run_preset(preset, args.full)


asyncio.run(main())
