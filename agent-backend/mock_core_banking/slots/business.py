from .core import INDUSTRY_OPTIONS, PHASE_1, PHASE_2, slot
from .financial import ASSETS, PHASE_6

IDENTITY_IDS = (
    "full_name", "date_of_birth", "mobile_number", "email_address",
    "residency_status", "visa_subclass", "visa_expiry_date",
)
LOAN_IDS = ("loan_amount", "loan_term_months", "repayment_frequency")
GUARANTOR_ASSET_IDS = ("owns_property", "property_equity_value", "savings_balance")

NOT_UNSECURED = "security_offered != 'unsecured'"


def _pick(slots: list[dict], ids: tuple[str, ...]) -> list[dict]:
    by_id = {s["id"]: s for s in slots}
    return [by_id[i] for i in ids]


BUSINESS_LOAN = _pick(PHASE_2, LOAN_IDS) + [
    slot(
        "loan_purpose", "Main use of funds", 2, "choice",
        "What the business will use the money for",
        options=[
            "working_capital", "equipment_purchase", "business_expansion", "stock_inventory",
            "commercial_property", "refinance_business_debt", "business_acquisition", "other",
        ],
        regulatory_basis="Responsible lending — requirements and objectives",
        group="purpose",
    ),
    slot(
        "purpose_detail", "Use of funds in detail", 2, "text",
        "Ask exactly what the money buys or pays for and how it helps the business; "
        "specific, not general — this is the strongest screen in business lending",
        regulatory_basis="Responsible lending — requirements and objectives",
        group="purpose",
    ),
]

BUSINESS_PROFILE = [
    slot("business_name", "Registered business name", 3, "text",
         "As registered with ASIC or the ABR",
         verification="asic_extract", group="business"),
    slot("abn_or_acn", "ABN or ACN", 3, "text",
         "The 11-digit ABN or 9-digit ACN",
         verification="asic_extract", group="business"),
    slot("entity_structure", "Entity structure", 3, "choice",
         "Drives which constituent documents are required",
         options=["sole_trader", "partnership", "company", "trust"],
         regulatory_basis="Entity verification", group="business"),
    slot("applicant_role", "Applicant's role in the business", 3, "choice",
         "Their position in the entity",
         options=["owner", "director", "partner", "trustee"],
         group="business"),
    slot("entity_documents_note", "Constituent documents", 3, "text",
         "Partnership agreement, trust deed or company constitution as applicable",
         required_when="entity_structure in ('partnership', 'company', 'trust')",
         verification="entity_documents", group="business"),
    slot("industry", "Industry", 3, "choice",
         "The closest industry; some industries are excluded or carry tighter policy",
         options=INDUSTRY_OPTIONS,
         regulatory_basis="Industry exclusions", group="business"),
    slot("years_trading", "Years trading", 3, "number",
         "How long the business has traded under this ABN; minimum trading period is a policy screen",
         validation={"min": 0},
         verification="tax_return", group="business"),
    slot("business_premises", "Business premises", 3, "choice",
         "Whether they own or lease where they operate, or run it from home",
         options=["owned", "leased", "home_based"],
         group="business"),
    slot("number_of_employees", "Number of employees", 3, "number",
         "Full-time equivalent staff, not counting the owners",
         validation={"min": 0},
         group="business"),
]

BUSINESS_FINANCIALS = [
    slot("annual_turnover", "Annual turnover", 4, "currency",
         "Total sales for the most recent financial year",
         validation={"min": 0},
         verification="financial_statements", group="business_financials"),
    slot("net_profit_before_tax", "Net profit before tax", 4, "currency",
         "For the most recent financial year; a loss is a negative number",
         verification="financial_statements", group="business_financials"),
    slot("turnover_trend", "Turnover trend", 4, "choice",
         "Compared with the year before",
         options=["growing", "stable", "declining"],
         group="business_financials"),
    slot("prior_year_annual_turnover", "Prior year annual turnover", 4, "currency",
         "Total sales for the financial year before the most recent one",
         required_when="years_trading >= 2",
         verification="financial_statements", group="business_financials"),
    slot("prior_year_net_profit_before_tax", "Prior year net profit before tax", 4, "currency",
         "For the financial year before the most recent one; a loss is a negative number",
         required_when="years_trading >= 2",
         verification="financial_statements", group="business_financials"),
    slot("two_years_prior_annual_turnover", "Annual turnover, two years prior", 4, "currency",
         "Total sales for the financial year two years before the most recent one",
         required_when="years_trading >= 3",
         verification="financial_statements", group="business_financials"),
    slot("two_years_prior_net_profit_before_tax", "Net profit before tax, two years prior", 4, "currency",
         "For the financial year two years before the most recent one; a loss is a negative number",
         required_when="years_trading >= 3",
         verification="financial_statements", group="business_financials"),
    slot("interest_expense_annual", "Annual interest expense", 4, "currency",
         "Total interest paid on all business debt in the most recent financial year; "
         "used to add back to net profit and to assess interest cover",
         validation={"min": 0},
         verification="financial_statements", group="business_financials"),
    slot("depreciation_amortisation_annual", "Annual depreciation and amortisation", 4, "currency",
         "Non-cash expense for the most recent financial year, added back to find true operating cash flow",
         validation={"min": 0},
         verification="financial_statements", group="business_financials"),
    slot("current_assets", "Current assets", 4, "currency",
         "Cash, receivables and other assets convertible to cash within 12 months, from the latest balance sheet",
         validation={"min": 0},
         verification="financial_statements", group="business_financials"),
    slot("current_liabilities", "Current liabilities", 4, "currency",
         "Liabilities due within 12 months, from the latest balance sheet",
         validation={"min": 0},
         verification="financial_statements", group="business_financials"),
    slot("total_business_liabilities", "Total business liabilities", 4, "currency",
         "All liabilities on the latest balance sheet, current and non-current",
         validation={"min": 0},
         verification="financial_statements", group="business_financials"),
    slot("total_business_equity", "Total business equity", 4, "currency",
         "Owners'/shareholders' equity on the latest balance sheet",
         verification="financial_statements", group="business_financials"),
    slot("existing_business_debt_repayments", "Existing business loan repayments per month", 4, "currency",
         "Total monthly repayments on business loans, overdrafts, equipment finance and cards; 0 if none",
         validation={"min": 0},
         per_month=True, group="business_financials"),
    slot("existing_business_lending", "Existing business lending details", 4, "text",
         "Who the lenders are and what each facility is",
         required=False,
         required_when="existing_business_debt_repayments > 0",
         group="business_financials"),
    slot("ato_obligations_current", "Tax obligations up to date", 4, "boolean",
         "BAS and tax returns lodged on time with no overdue ATO debt",
         verification="ato_portal_statement",
         regulatory_basis="Credit policy — tax compliance", group="business_financials"),
    slot("ato_debt_detail", "ATO debt or payment plan", 4, "text",
         "Only when tax obligations are not up to date: how much is owed and any payment plan",
         required_when="ato_obligations_current == False",
         group="business_financials"),
    slot("projected_revenue_growth_pct", "Projected revenue growth", 4, "number",
         "Management's forecast revenue growth for this expansion, as a percentage; "
         "stress-tested with a haircut before being relied on",
         required=False,
         required_when="loan_purpose == 'business_expansion'",
         validation={"min": -100, "max": 500},
         group="business_financials"),
]

SECURITY = [
    slot("security_offered", "Security offered", 5, "choice",
         "What the loan will be secured against, if anything",
         options=["commercial_property", "residential_property", "business_assets", "equipment", "unsecured"],
         group="security"),
    slot("security_value", "Estimated value of the security", 5, "currency",
         "Their estimate; verified by valuation later",
         required_when=NOT_UNSECURED,
         validation={"min": 0},
         verification="valuation", group="security"),
    slot("director_guarantee_accepted", "Personal guarantee understood", 5, "boolean",
         "Owners and directors are normally required to guarantee personally, which means "
         "their personal position is assessed too — confirm they understand",
         regulatory_basis="Guarantor disclosure", group="security"),
]

BUSINESS_SLOTS = (
    _pick(PHASE_1, IDENTITY_IDS)
    + BUSINESS_LOAN
    + BUSINESS_PROFILE
    + BUSINESS_FINANCIALS
    + SECURITY
    + [{**s, "phase": 5} for s in _pick(ASSETS, GUARANTOR_ASSET_IDS)]
    + PHASE_6
)
