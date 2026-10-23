import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core import observability
from app.agents.output_schemas import TransactionCategories
from app.core.llm import as_text, get_llm
from app.core.output_guard import parse_json

TRANSACTION_CATEGORIES = [
    "exp_food_groceries", "exp_clothing_personal_care", "exp_recreation_holidays",
    "exp_education_childcare", "exp_insurance", "exp_medical_health",
    "exp_rent_board", "exp_other_housing", "exp_phone_internet_media",
    "exp_vehicle_transport", "income", "transfer", "other",
]

BUSINESS_TRANSACTION_CATEGORIES = [
    "sales_revenue", "other_business_income", "loan_proceeds", "capital_injection",
    "wages_super", "supplier_payment", "rent_premises", "ato_payment", "loan_repayment",
    "owner_drawings", "bank_fees", "dishonour", "transfer", "other",
]

SYSTEM = """You categorize bank transactions for a loan serviceability assessment.

You are given a list of transactions (date, description, amount, direction)
and the fixed list of valid categories. Assign exactly one category to each.

Return ONLY a JSON object, no markdown fences:
{"categorized": [{"index": 0, "category": "<one of the given categories>"}, ...]}

Rules:
- Only ever use a category from the list given. Never invent one.
- Debit transactions map to one of the exp_* categories, or "other" if genuinely unclear.
- Credit transactions: "income" if it looks like salary/regular income, "transfer"
  if it looks like a transfer between the applicant's own accounts, "other" for
  anything else (a one-off gift, tax refund, loan).
- Judge only from the description text given. Do not guess intent beyond what a
  reasonable person would infer from the wording."""

BUSINESS_SYSTEM = """You categorize business bank transactions for a business loan assessment.

You are given a list of transactions (date, description, amount, direction)
and the fixed list of valid categories. Assign exactly one category to each.

Return ONLY a JSON object, no markdown fences:
{"categorized": [{"index": 0, "category": "<one of the given categories>"}, ...]}

Rules:
- Only ever use a category from the list given. Never invent one.
- Credits: "sales_revenue" for customer receipts, card settlements and invoice
  payments; "loan_proceeds" for a loan or finance drawdown; "capital_injection"
  for money the owners put in; "transfer" between the business's own accounts;
  "other_business_income" for anything else that is clearly income (interest,
  a grant, a rebate); "other" if unclear.
- Debits: "loan_repayment" for repayments to a lender, equipment finance or a
  business card; "ato_payment" for payments to the ATO; "wages_super" for payroll
  and superannuation; "rent_premises" for rent on the business premises;
  "owner_drawings" for money taken out by the owners; "bank_fees" for fees and
  charges; "dishonour" for a dishonoured or reversed payment or its fee;
  "supplier_payment" for stock, materials and running costs; "transfer" between
  the business's own accounts; "other" if unclear.
- Judge only from the description text given."""


@observability.traced("document.categorize-transactions", as_type="chain")
async def categorize_transactions(transactions: list[dict], business: bool = False) -> list[dict]:
    if not transactions:
        return []

    categories = BUSINESS_TRANSACTION_CATEGORIES if business else TRANSACTION_CATEGORIES

    payload = {
        "categories": categories,
        "transactions": [
            {"index": i, "date": t.get("date"), "description": t.get("description"),
             "amount": t.get("amount"), "direction": t.get("direction")}
            for i, t in enumerate(transactions)
        ],
    }

    llm = get_llm("document")
    resp = await llm.ainvoke([
        SystemMessage(content=BUSINESS_SYSTEM if business else SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ])

    parsed = parse_json(as_text(resp), TransactionCategories, "document-categorize") or {}

    category_by_index = {
        c["index"]: c["category"]
        for c in parsed.get("categorized") or []
        if c.get("category") in categories
    }

    return [{**t, "category": category_by_index.get(i, "other")} for i, t in enumerate(transactions)]