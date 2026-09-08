"""Synthetic development identities for the mock credit bureau sandbox.

NONE of the people below are real. Names, dates of birth and addresses are made up for
local development and testing only, spanning the score bands a real bureau response would
return. Never treat this data as representative of any real individual.
"""

from typing import Any, TypedDict


class ReportSummary(TypedDict):
    enquiries_last_6_months: int
    adverse_events: int
    repayment_history: str
    oldest_account_years: int
    accounts_open: int


class Identity(TypedDict):
    name: str
    dob: str
    address: str
    score: int
    band: str
    report_summary: ReportSummary


SYNTHETIC_IDENTITIES: list[Identity] = [
    # Excellent (800+)
    {
        "name": "Priya Natarajan",
        "dob": "1985-03-14",
        "address": "12 Wattle Street, Northcote VIC 3070",
        "score": 831,
        "band": "excellent",
        "report_summary": {
            "enquiries_last_6_months": 0,
            "adverse_events": 0,
            "repayment_history": "no missed payments in 24 months",
            "oldest_account_years": 14,
            "accounts_open": 3,
        },
    },
    # Good (700-799) — matches the worked example in the platform spec.
    {
        "name": "Daniel Osei",
        "dob": "1990-07-22",
        "address": "45 Banksia Avenue, Marrickville NSW 2204",
        "score": 742,
        "band": "good",
        "report_summary": {
            "enquiries_last_6_months": 2,
            "adverse_events": 0,
            "repayment_history": "no missed payments in 24 months",
            "oldest_account_years": 8,
            "accounts_open": 4,
        },
    },
    # Fair (650-699)
    {
        "name": "Melissa Chan",
        "dob": "1993-11-02",
        "address": "8 Grevillea Court, Toowoomba QLD 4350",
        "score": 671,
        "band": "fair",
        "report_summary": {
            "enquiries_last_6_months": 4,
            "adverse_events": 0,
            "repayment_history": "1 missed payment in 24 months",
            "oldest_account_years": 5,
            "accounts_open": 5,
        },
    },
    # Poor (below 650)
    {
        "name": "Wayne Fitzgerald",
        "dob": "1978-01-30",
        "address": "3 Hakea Place, Elizabeth SA 5112",
        "score": 588,
        "band": "poor",
        "report_summary": {
            "enquiries_last_6_months": 7,
            "adverse_events": 1,
            "repayment_history": "3 missed payments in 24 months",
            "oldest_account_years": 6,
            "accounts_open": 6,
        },
    },
    # Adverse events on file
    {
        "name": "Bradley Simmons",
        "dob": "1982-09-09",
        "address": "21 Currawong Crescent, Frankston VIC 3199",
        "score": 512,
        "band": "poor",
        "report_summary": {
            "enquiries_last_6_months": 5,
            "adverse_events": 2,
            "repayment_history": "default listed 2024-02, 4 missed payments in 24 months",
            "oldest_account_years": 9,
            "accounts_open": 4,
        },
    },
    # Thin-file applicant — short credit history, few accounts.
    {
        "name": "Aisha Yusuf",
        "dob": "2001-05-18",
        "address": "60 Correa Way, Joondalup WA 6027",
        "score": 663,
        "band": "fair",
        "report_summary": {
            "enquiries_last_6_months": 1,
            "adverse_events": 0,
            "repayment_history": "no missed payments in 8 months",
            "oldest_account_years": 1,
            "accounts_open": 1,
        },
    },
]


def _normalize(value: str) -> str:
    return " ".join(value.split()).strip().lower()


def find_identity(name: str, dob: str, address: str) -> Identity | None:
    """Matches on normalised name, dob and address. All three must match — a real bureau
    match is stricter than any single field, so a partial match is treated as no match."""
    target = (_normalize(name), _normalize(dob), _normalize(address))
    for identity in SYNTHETIC_IDENTITIES:
        candidate = (
            _normalize(identity["name"]),
            _normalize(identity["dob"]),
            _normalize(identity["address"]),
        )
        if candidate == target:
            return identity
    return None


def report_payload(identity: Identity) -> dict[str, Any]:
    return {
        "matched": True,
        "score": identity["score"],
        "band": identity["band"],
        "report_summary": identity["report_summary"],
    }
