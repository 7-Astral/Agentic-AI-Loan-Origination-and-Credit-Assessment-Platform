from enum import Enum

from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class BankStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class LoanType(str, Enum):
    home = "home"
    investment = "investment"
    personal = "personal"
    car = "car"
    business = "business"


class ConversationStatus(str, Enum):
    active = "active"
    completed = "completed"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class UserRole(str, Enum):
    customer = "customer"
    loan_officer = "loan_officer"
    credit_manager = "credit_manager"
    admin = "admin"


class ApplicationStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    in_review = "in_review"
    decided = "decided"


class OfficerActionType(str, Enum):
    approve = "approve"
    reject = "reject"
    override = "override"
    request_info = "request_info"


def _pg_enum(enum_cls: type[Enum], name: str) -> PGEnum:
    # Pass the Enum *class* (not a bare list of strings) so SQLAlchemy converts DB values
    # to/from real Python enum members instead of plain strings.
    return PGEnum(
        enum_cls, name=name, create_type=False, values_callable=lambda cls: [m.value for m in cls]
    )


# Shared native Postgres enum types. `create_type=False` because the migration creates the
# types explicitly (once) — these definitions must match the migration exactly.
bank_status_enum = _pg_enum(BankStatus, "bank_status")
loan_type_enum = _pg_enum(LoanType, "loan_type")
conversation_status_enum = _pg_enum(ConversationStatus, "conversation_status")
message_role_enum = _pg_enum(MessageRole, "message_role")
user_role_enum = _pg_enum(UserRole, "user_role")
application_status_enum = _pg_enum(ApplicationStatus, "application_status")
officer_action_type_enum = _pg_enum(OfficerActionType, "officer_action_type")
