import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import as_text, get_llm

TRANSACTION_CATEGORIES = [
    "exp_food_groceries", "exp_clothing_personal_care", "exp_recreation_holidays",
    "exp_education_childcare", "exp_insurance", "exp_medical_health",
    "exp_rent_board", "exp_other_housing", "exp_phone_internet_media",
    "exp_vehicle_transport", "income", "transfer", "other",
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


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """Returns the same transactions, each with a validated 'category' key added."""
    if not transactions:
        return []

    payload = {
        "categories": TRANSACTION_CATEGORIES,
        "transactions": [
            {"index": i, "date": t.get("date"), "description": t.get("description"),
             "amount": t.get("amount"), "direction": t.get("direction")}
            for i, t in enumerate(transactions)
        ],
    }

    llm = get_llm("document")
    resp = await llm.ainvoke([
        SystemMessage(content=SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ])

    try:
        parsed = _parse(as_text(resp))
    except (json.JSONDecodeError, IndexError):
        parsed = {"categorized": []}

    category_by_index = {
        c["index"]: c["category"]
        for c in parsed.get("categorized", [])
        if c.get("category") in TRANSACTION_CATEGORIES
    }

    return [{**t, "category": category_by_index.get(i, "other")} for i, t in enumerate(transactions)]