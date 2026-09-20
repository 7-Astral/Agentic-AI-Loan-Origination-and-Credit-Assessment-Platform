"""Core slot definitions — asked for every product.

Phases 4-7 and product overlays are added in the next slice.
"""


def slot(
    slot_id,
    label,
    phase,
    type_,
    ask_hint,
    *,
    options=None,
    required=True,
    required_when=None,
    sources=("ask",),
    validation=None,
    verification=None,
    regulatory_basis=None,
    group=None,
):
    """Build one slot definition.

    required_when is a Python expression evaluated against filled slots.
    None means always required (when `required` is True).
    sources is the fill-order preference, cheapest first.
    """
    return {
        "id": slot_id,
        "label": label,
        "phase": phase,
        "group": group,
        "type": type_,
        "options": list(options) if options else None,
        "required": required,
        "required_when": required_when,
        "sources": list(sources),
        "validation": validation or {},
        "verification": verification,
        "regulatory_basis": regulatory_basis,
        "ask_hint": ask_hint,
    }


EMPLOYED = "employment_status in ('full_time', 'part_time', 'casual')"

# Phase 2 — requirements and objectives
PHASE_2 = [
    slot(
        "loan_amount", "Amount to borrow", 2, "currency",
        "How much they need, and whether it matches the purpose",
        validation={"min": 1000},
        regulatory_basis="NCCP requirements and objectives",
        group="loan",
    ),
    slot(
        "loan_term_months", "Loan term in months", 2, "number",
        "Preferred repayment period; accept years and convert",
        validation={"min": 6, "max": 360},
        regulatory_basis="NCCP requirements and objectives",
        group="loan",
    ),
    slot(
        "repayment_frequency", "Repayment frequency", 2, "choice",
        "How often they want to repay; align with their pay cycle",
        options=["weekly", "fortnightly", "monthly"],
        regulatory_basis="NCCP requirements and objectives",
        group="loan",
    ),
    slot(
        "loan_purpose", "Main purpose", 2, "choice",
        "What the money is for; screen against excluded purposes",
        options=[
            "purchase_property", "purchase_vehicle", "debt_consolidation",
            "home_improvement", "business_use", "travel", "medical",
            "education", "other",
        ],
        regulatory_basis="NCCP requirements and objectives",
        group="purpose",
    ),
    slot(
        "purpose_detail", "Purpose in their own words", 2, "text",
        "Ask them to describe it; this is the inquiry a form cannot do",
        regulatory_basis="NCCP requirements and objectives",
        group="purpose",
    ),
    slot(
        "foreseeable_changes", "Foreseeable changes to circumstances", 2, "text",
        "Anything expected to change repayment ability during the term",
        required=False,
        regulatory_basis="NCCP reasonable inquiries",
        group="purpose",
    ),
]

# Phase 1 — identity and household
PHASE_1 = [
    slot(
        "full_name", "Full legal name", 1, "text",
        "Exactly as it appears on their ID",
        verification="primary_photo_id",
        group="identity",
    ),
    slot(
        "date_of_birth", "Date of birth", 1, "date",
        "Needed for identity and the 18+ check",
        validation={"min_age": 18},
        verification="primary_photo_id",
        group="identity",
    ),
    slot(
        "mobile_number", "Mobile number", 1, "phone",
        "Contact number for the application",
        group="identity",
    ),
    slot(
        "email_address", "Email address", 1, "email",
        "Where documents and the assessment copy are sent",
        group="identity",
    ),
    slot(
        "residency_status", "Residency status", 1, "choice",
        "Citizen, permanent resident, or temporary visa",
        options=["citizen", "permanent_resident", "temporary_visa"],
        regulatory_basis="Lending policy eligibility",
        group="identity",
    ),
    slot(
        "visa_subclass", "Visa subclass", 1, "text",
        "Only when on a temporary visa",
        required_when="residency_status == 'temporary_visa'",
        group="identity",
    ),
    slot(
        "tax_resident_au", "Australian tax resident", 1, "boolean",
        "Regulatory question, not a credit one — say so",
        regulatory_basis="Tax residency declaration",
        group="identity",
    ),
    slot(
        "marital_status", "Marital status", 1, "choice",
        "Affects how household expenses are treated",
        options=["single", "married", "de_facto", "separated", "divorced", "widowed"],
        group="household",
    ),
    slot(
        "dependants", "Number of financial dependants", 1, "number",
        "Explain the breadth: children of any age, and anyone else supported",
        validation={"min": 0, "max": 15},
        regulatory_basis="Expense benchmarking",
        group="household",
    ),
    slot(
        "living_arrangement", "Living arrangement", 1, "choice",
        "Owner, renting (on the lease), or boarding (neither on lease nor owning)",
        options=["own_outright", "own_with_mortgage", "renting", "boarding",
                 "living_with_family"],
        regulatory_basis="Expense treatment",
        group="household",
    ),
    slot(
        "current_address", "Current residential address", 1, "address",
        "Full street address, not a PO box",
        verification="proof_of_address",
        group="household",
    ),
    slot(
        "years_at_address", "Years at current address", 1, "number",
        "Determines whether prior address history is needed",
        validation={"min": 0},
        group="household",
    ),
    slot(
        "previous_address", "Previous address", 1, "address",
        "Only when under three years at the current one",
        required_when="years_at_address < 3",
        group="household",
    ),
]

# Phase 3 — employment and income
PHASE_3 = [
    slot(
        "employment_status", "Employment status", 3, "choice",
        "Current status; drives which follow-ups apply",
        options=["full_time", "part_time", "casual", "self_employed",
                 "retired", "unemployed", "student"],
        sources=("extracted", "ask"),
        verification="payslip_or_contract",
        group="employment",
    ),
    slot(
        "employer_name", "Employer name", 3, "text",
        "Who pays them",
        required_when=EMPLOYED,
        sources=("extracted", "ask"),
        verification="payslip_or_contract",
        group="employment",
    ),
    slot(
        "job_title", "Job title", 3, "text",
        "Their role",
        required_when=EMPLOYED,
        sources=("extracted", "ask"),
        group="employment",
    ),
    slot(
        "months_in_current_role", "Months in current role", 3, "number",
        "Tenure; under six months triggers a probation follow-up",
        required_when=f"{EMPLOYED} or employment_status == 'self_employed'",
        validation={"min": 0},
        group="employment",
    ),
    slot(
        "on_probation", "Currently on probation", 3, "boolean",
        "Only when under six months in the role",
        required_when="months_in_current_role < 6",
        regulatory_basis="Income stability assessment",
        group="employment",
    ),
    slot(
        "abn_years_trading", "Years trading under ABN", 3, "number",
        "Self-employed equivalent of tenure",
        required_when="employment_status == 'self_employed'",
        validation={"min": 0},
        verification="tax_return",
        group="employment",
    ),
    slot(
        "gross_annual_income", "Gross annual income", 3, "currency",
        "Before tax; accept any frequency and normalise",
        sources=("extracted", "ask"),
        validation={"min": 0},
        verification="payslip_or_tax_return",
        regulatory_basis="Financial situation inquiry",
        group="income",
    ),
    slot(
        "net_income_amount", "Net income per pay period", 3, "currency",
        "After tax, as it lands in their account",
        sources=("extracted", "ask"),
        validation={"min": 0},
        verification="bank_statements",
        regulatory_basis="Financial situation inquiry",
        group="income",
    ),
    slot(
        "net_income_frequency", "Net income frequency", 3, "choice",
        "The pay cycle the net amount refers to",
        options=["weekly", "fortnightly", "monthly", "annually"],
        sources=("extracted", "ask"),
        group="income",
    ),
    slot(
        "other_income", "Other income sources", 3, "text",
        "Rental, government payments, dividends, second job",
        required=False,
        regulatory_basis="Financial situation inquiry",
        group="income",
    ),
]

CORE_SLOTS = PHASE_1 + PHASE_2 + PHASE_3