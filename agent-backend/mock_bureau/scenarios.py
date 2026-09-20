import hashlib
import random
from datetime import date, timedelta
from typing import Callable

MONTH_DAYS = 30

CARD_CREDITORS = ["Westpac", "ANZ", "Commonwealth Bank", "NAB", "Citi"]
LOAN_CREDITORS = ["Latitude", "Plenti", "Society One", "Now Finance", "Wisr"]


def _ago(today: date, months: float) -> str:
    return (today - timedelta(days=round(months * MONTH_DAYS))).isoformat()


def _account(rng: random.Random, kind: str, *, months_open: int, limit: int = 0, balance: int = 0,
             repayment: int = 0, status: str = "open", late: dict[int, int] | None = None) -> dict:
    history = [0] * min(months_open, 24)
    for month_index, code in (late or {}).items():
        if month_index < len(history):
            history[month_index] = code
    creditors = CARD_CREDITORS if kind == "credit_card" else LOAN_CREDITORS
    return {
        "account_id": f"ACC-{rng.randrange(10**6):06d}",
        "type": kind,
        "creditor": rng.choice(creditors),
        "status": status,
        "limit": limit,
        "balance": balance,
        "monthly_repayment": repayment,
        "rhi": history,
    }


def _enquiry(rng: random.Random, today: date, months: float, kind: str, amount: int) -> dict:
    return {"date": _ago(today, months), "credit_type": kind, "amount": amount,
            "enquirer": rng.choice(CARD_CREDITORS + LOAN_CREDITORS)}


def _file(score: int, *, accounts=None, defaults=None, enquiries=None,
          insolvency=None, judgments=None, hardship=None) -> dict:
    return {
        "score": score,
        "accounts": accounts or [],
        "defaults": defaults or [],
        "enquiries": enquiries or [],
        "insolvency": insolvency,
        "judgments": judgments or [],
        "hardship": hardship or [],
    }


def _clean_card(rng: random.Random, **late) -> dict:
    return _account(rng, "credit_card", months_open=60, limit=5000, balance=rng.randrange(200, 1200), **late)


def prime(rng: random.Random, today: date) -> dict:
    paid_off_car = _account(rng, "auto_loan", months_open=48, status="closed")
    return _file(
        rng.randint(840, 880),
        accounts=[_clean_card(rng), paid_off_car],
        enquiries=[_enquiry(rng, today, 5, "credit_card", 5000)],
    )


def minor_arrears(rng: random.Random, today: date) -> dict:
    card = _clean_card(rng, late={9: 1, 10: 1})
    return _file(
        rng.randint(620, 660),
        accounts=[card],
        enquiries=[_enquiry(rng, today, 3, "personal_loan", 15000), _enquiry(rng, today, 11, "bnpl", 800)],
    )


def recent_arrears(rng: random.Random, today: date) -> dict:
    card = _clean_card(rng, late={1: 2, 2: 1})
    return _file(rng.randint(520, 560), accounts=[card],
                 enquiries=[_enquiry(rng, today, 2, "personal_loan", 10000)])


def thin_file(rng: random.Random, today: date) -> dict:
    return _file(rng.randint(450, 490))


def enquiry_spree(rng: random.Random, today: date) -> dict:
    kinds = ["personal_loan", "credit_card", "bnpl", "personal_loan", "auto_loan", "credit_card", "bnpl"]
    enquiries = [_enquiry(rng, today, m, kind, rng.choice([2000, 8000, 15000]))
                 for m, kind in zip([0.3, 0.8, 1.2, 2, 3, 4, 5], kinds)]
    return _file(rng.randint(570, 610), accounts=[_clean_card(rng)], enquiries=enquiries)


def hardship(rng: random.Random, today: date) -> dict:
    card = _clean_card(rng)
    arrangements = [
        {"date": _ago(today, 4), "account_id": card["account_id"], "arrangement": "repayment_deferral"},
        {"date": _ago(today, 9), "account_id": card["account_id"], "arrangement": "reduced_repayments"},
    ]
    return _file(rng.randint(590, 630), accounts=[card], hardship=arrangements)


def undisclosed_debt(rng: random.Random, today: date) -> dict:
    loan = _account(rng, "personal_loan", months_open=14, balance=21000, repayment=640)
    bnpl = _account(rng, "bnpl", months_open=6, balance=900, repayment=90)
    return _file(rng.randint(690, 730), accounts=[_clean_card(rng), loan, bnpl])


def paid_default(rng: random.Random, today: date) -> dict:
    listed = {"creditor": "Telstra", "amount": 1850, "status": "paid",
              "listed_date": _ago(today, 36), "paid_date": _ago(today, 22)}
    return _file(rng.randint(550, 580), accounts=[_clean_card(rng)], defaults=[listed])


def unpaid_default(rng: random.Random, today: date) -> dict:
    listed = {"creditor": "Optus", "amount": 2340, "status": "unpaid",
              "listed_date": _ago(today, 14), "paid_date": None}
    card = _clean_card(rng, late={15: 3, 16: 3})
    return _file(rng.randint(370, 410), accounts=[card], defaults=[listed])


def judgment(rng: random.Random, today: date) -> dict:
    ruling = {"date": _ago(today, 18), "amount": 6200, "court": "Local Court of NSW", "status": "unsatisfied"}
    return _file(rng.randint(380, 420), accounts=[_clean_card(rng)], judgments=[ruling])


def bankrupt(rng: random.Random, today: date) -> dict:
    return _file(rng.randint(200, 260),
                 insolvency={"type": "bankruptcy", "start_date": _ago(today, 20), "discharge_date": None})


SCENARIOS: dict[str, tuple[str, Callable[[random.Random, date], dict], int]] = {
    "prime": ("Clean file, one recent enquiry", prime, 45),
    "minor_arrears": ("Two 30-day late payments about 10 months ago", minor_arrears, 20),
    "thin_file": ("No credit accounts or history", thin_file, 8),
    "enquiry_spree": ("Seven enquiries in the last 6 months", enquiry_spree, 6),
    "recent_arrears": ("60-day arrears within the last 3 months", recent_arrears, 5),
    "hardship": ("Two hardship arrangements in the last 12 months", hardship, 4),
    "undisclosed_debt": ("Open personal loan and BNPL an applicant may not declare", undisclosed_debt, 4),
    "paid_default": ("One default, since paid", paid_default, 4),
    "unpaid_default": ("One unpaid default and 90-day arrears", unpaid_default, 2),
    "judgment": ("Unsatisfied court judgment", judgment, 1),
    "bankrupt": ("Current bankruptcy", bankrupt, 1),
}


def identity_seed(full_name: str, date_of_birth: date) -> int:
    key = f"{' '.join(full_name.lower().split())}|{date_of_birth.isoformat()}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)


def pick_scenario(seed: int) -> str:
    roll = seed % sum(w for _, _, w in SCENARIOS.values())
    for name, (_, _, weight) in SCENARIOS.items():
        if roll < weight:
            return name
        roll -= weight
    raise AssertionError("unreachable: weights exhausted")


def band(score: int) -> str:
    if score >= 833:
        return "excellent"
    if score >= 726:
        return "very_good"
    if score >= 622:
        return "good"
    if score >= 510:
        return "average"
    return "below_average"
