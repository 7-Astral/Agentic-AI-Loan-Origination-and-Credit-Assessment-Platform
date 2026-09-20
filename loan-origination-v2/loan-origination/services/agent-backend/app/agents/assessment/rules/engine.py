from simpleeval import simple_eval

from app.agents.assessment.metric import Metric

SEVERITY_ORDER = {"fail": 0, "flag": 1, "provisional": 2, "pass": 3}


def evaluate(rules: list[dict], metrics: dict[str, Metric], framework: str) -> list[dict]:
    scope = {name: m.value for name, m in metrics.items() if m.usable}

    results = []
    for rule in rules:
        if rule["framework"] != framework:
            continue

        missing = [r for r in rule["requires"] if r not in scope]
        if missing:
            results.append({
                "rule_id": rule["rule_id"],
                "status": "provisional",
                "missing": missing,
                "message": rule.get("message", ""),
            })
            continue

        try:
            triggered = simple_eval(rule["when"], names=scope)
        except Exception as exc:
            results.append({
                "rule_id": rule["rule_id"],
                "status": "error",
                "detail": str(exc),
            })
            continue

        if triggered:
            results.append({
                "rule_id": rule["rule_id"],
                "status": rule["status"],
                "message": rule.get("message", ""),
                "inputs": {k: scope[k] for k in rule["requires"]},
            })

    return sorted(results, key=lambda r: SEVERITY_ORDER.get(r["status"], 99))


def route(rule_results: list[dict], loan_amount: float | None = None) -> dict:
    statuses = {r["status"] for r in rule_results}

    if "fail" in statuses:
        tier = "decline_recommended"
    elif "provisional" in statuses:
        tier = "conditional"
    elif "flag" in statuses:
        tier = "underwriter_review"
    else:
        tier = "auto_eligible"

    return {
        "tier": tier,
        "fail_count": sum(1 for r in rule_results if r["status"] == "fail"),
        "flag_count": sum(1 for r in rule_results if r["status"] == "flag"),
        "provisional_count": sum(1 for r in rule_results if r["status"] == "provisional"),
    }