from agents.risk_assessment.completeness import compute_completeness_score, compute_missing_fields
from agents.risk_assessment.normalise import normalise_application
from schemas.risk_assessment import RequiredField

FIELDS = [
    RequiredField(key="applicant.name", five_c="character", requirement="required", label="Name"),
    RequiredField(key="applicant.dob", five_c="character", requirement="required", label="DOB"),
    RequiredField(
        key="applicant.employment.income",
        five_c="capacity",
        requirement="required",
        label="Income",
    ),
    RequiredField(
        key="applicant.employment.income_frequency",
        five_c="capacity",
        requirement="confidence",
        label="Income frequency",
    ),
    RequiredField(
        key="collateral.estimated_value",
        five_c="collateral",
        requirement="required",
        label="Asset value",
    ),
]


def test_missing_fields_identifies_gaps_and_attributes_correct_c() -> None:
    normalized = normalise_application(
        {"applicant": {"name": "Daniel Osei", "employment": {"income": 90000}}}
    )
    missing = compute_missing_fields(normalized, FIELDS)
    missing_keys = {m.field for m in missing}

    assert missing_keys == {
        "applicant.dob",
        "applicant.employment.income_frequency",
        "collateral.estimated_value",
    }

    by_key = {m.field: m for m in missing}
    assert by_key["applicant.dob"].five_c == "character"
    assert by_key["applicant.dob"].requirement == "required"
    assert by_key["applicant.employment.income_frequency"].five_c == "capacity"
    assert by_key["applicant.employment.income_frequency"].requirement == "confidence"
    assert by_key["collateral.estimated_value"].five_c == "collateral"


def test_no_missing_fields_when_all_present() -> None:
    normalized = normalise_application(
        {
            "applicant": {
                "name": "Daniel Osei",
                "dob": "1990-07-22",
                "employment": {"income": 90000, "income_frequency": "Annually"},
            },
            "collateral": {"estimated_value": 40000},
        }
    )
    missing = compute_missing_fields(normalized, FIELDS)
    assert missing == []


def test_completeness_score_reflects_proportion_present() -> None:
    normalized = normalise_application(
        {"applicant": {"name": "Daniel Osei", "employment": {"income": 90000}}}
    )
    missing = compute_missing_fields(normalized, FIELDS)
    score = compute_completeness_score(FIELDS, missing)
    assert score == 0.4  # 2 of 5 present


def test_completeness_score_is_one_when_checklist_empty() -> None:
    normalized = normalise_application({})
    assert compute_completeness_score([], compute_missing_fields(normalized, [])) == 1.0
