import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


class BankStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LoanType(str, enum.Enum):
    PERSONAL = "personal"
    BUSINESS = "business"
    HOME = "home"
    AUTO = "auto"
    EDUCATION = "education"


class LoanStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"


class EmploymentType(str, enum.Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class AgentType(str, enum.Enum):
    INTAKE = "intake"
    CREDIT_ASSESSMENT = "credit_assessment"
    DOCUMENT_VERIFICATION = "document_verification"
    DECISION = "decision"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"


class MessageSender(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


class DecisionType(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class DecisionResult(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class EscalationStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
