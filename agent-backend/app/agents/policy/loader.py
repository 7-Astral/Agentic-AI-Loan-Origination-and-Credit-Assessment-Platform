import csv
from pathlib import Path

from app.core.config import get_settings

SECTION_HEADERS = {
    "CORPORATE BANKS",
    "MUTUAL / MEMBER-OWNED BANKS",
}

IGNORED_FIELDS = {
    "Bank",
    "Bank Type",
    "Loan Type",
}

SOURCE = "banks_policy.csv"
DATA_STATUS = "synthetic_demo_policy"


def policy_file() -> Path:
    return Path(get_settings().policy_csv_path)


def load_policy_rows() -> list[dict[str, str]]:
    path = policy_file()
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")

    policies: list[dict[str, str]] = []
    headers: list[str] | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.reader(file):
            if not row:
                continue

            first_value = row[0].strip()
            if first_value in SECTION_HEADERS:
                continue
            if first_value == "Bank":
                headers = [value.strip() for value in row]
                continue
            if headers is None:
                continue

            values = row[: len(headers)]
            values += [""] * (len(headers) - len(values))
            policy = {headers[i]: values[i].strip() for i in range(len(headers))}
            if policy.get("Bank"):
                policies.append(policy)

    return policies


def create_policy_chunks(policies: list[dict[str, str]]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []

    for policy in policies:
        bank = policy.get("Bank", "")
        bank_type = policy.get("Bank Type", "")
        loan_type = policy.get("Loan Type", "")
        if not bank or not loan_type:
            continue

        for category, value in policy.items():
            if category in IGNORED_FIELDS or not value:
                continue

            chunks.append(
                {
                    "bank": bank,
                    "bank_type": bank_type,
                    "loan_type": loan_type,
                    "category": category,
                    "content": (
                        f"Bank: {bank}\n"
                        f"Bank Type: {bank_type}\n"
                        f"Loan Type: {loan_type}\n"
                        f"Policy Category: {category}\n"
                        f"Policy Rule: {value}"
                    ),
                    "source": SOURCE,
                    "data_status": DATA_STATUS,
                }
            )

    return chunks
