from app.agents.interaction.prefill import prefill_from_profile
from mock_core_banking.slots.registry import schema_for

PERSONAL_EMPLOYMENT = {"employment_status", "employer_name", "job_title", "gross_annual_income", "net_income_amount"}
HOUSEHOLD = {"marital_status", "dependants", "living_arrangement", "exp_food_groceries"}


def slot_ids(schema: dict) -> set[str]:
    return {s["id"] for s in schema["slots"]}


def test_business_interview_asks_about_the_business_not_a_salary():
    ids = slot_ids(schema_for("BUSINESS-AB12CD34", loan_type="business", category="term"))

    assert {"business_name", "abn_or_acn", "annual_turnover", "net_profit_before_tax", "ato_obligations_current"} <= ids
    assert not ids & PERSONAL_EMPLOYMENT
    assert not ids & HOUSEHOLD


def test_platform_product_codes_get_their_category_questions():
    home = slot_ids(schema_for("HOME-AB12CD34", loan_type="home", category="owner_occupied"))
    vehicle = slot_ids(schema_for("AUTO-AB12CD34", loan_type="personal", category="vehicle"))
    personal = slot_ids(schema_for("PERSONAL-AB12CD34", loan_type="personal", category="general"))

    assert {"property_price", "deposit_amount"} <= home
    assert {"vehicle_purchase_price", "vehicle_year"} <= vehicle
    assert "property_price" not in personal and "vehicle_year" not in personal


def test_schemas_have_unique_slot_ids():
    for loan_type, category in [("business", "term"), ("home", "owner_occupied"), ("personal", "vehicle")]:
        slots = schema_for("X-1", loan_type=loan_type, category=category)["slots"]
        assert len(slots) == len({s["id"] for s in slots})


def test_registration_details_prefill_and_skip_invalid_values():
    slots = schema_for("PERSONAL-AB12CD34", loan_type="personal", category="general")["slots"]
    profile = {"full_name": "Jordan Customer", "email": "customer@bank.com", "phone": None, "date_of_birth": "not-a-date"}

    filled, provenance = prefill_from_profile(slots, profile)

    assert filled == {"full_name": "Jordan Customer", "email_address": "customer@bank.com"}
    assert provenance["full_name"] == {"source": "profile", "turn": 0}
