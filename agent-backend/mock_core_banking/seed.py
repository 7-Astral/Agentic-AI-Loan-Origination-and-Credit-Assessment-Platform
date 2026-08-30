import asyncio

from mock_core_banking.db import engine, async_session
from mock_core_banking.models import Base, LoanType, Category, Product
from mock_core_banking.models import Base, LoanType, Category, Product, DocumentType, DocumentRequirement
LOAN_TYPES = [
    {"code": "personal", "name": "Personal Loan",
     "description": "Unsecured or secured loan for personal use, including vehicles."},
    {"code": "home", "name": "Home Loan",
     "description": "Loan to buy, refinance, or invest in residential property."},
    {"code": "business", "name": "Business Loan",
     "description": "Term finance for business purposes."},
]

CATEGORIES = [
    {"loan_type_code": "personal", "code": "general", "name": "General"},
    {"loan_type_code": "personal", "code": "vehicle", "name": "Vehicle"},
    {"loan_type_code": "home", "code": "owner_occupied", "name": "Owner Occupied"},
    {"loan_type_code": "home", "code": "investment", "name": "Investment"},
    {"loan_type_code": "business", "code": "term", "name": "Term"},
    {"loan_type_code": "business", "code": "overdraft", "name": "Overdraft"},
    {"loan_type_code": "business", "code": "equipment", "name": "Equipment Finance"},
]

PRODUCTS = [
    {"product_code": "PL-STD-001", "name": "Standard Personal Loan",
     "loan_type_code": "personal", "category_code": "general", "secured": False,
     "min_amount": 5000, "max_amount": 50000, "min_term_months": 12, "max_term_months": 84,
     "interest_rate": 9.99, "comparison_rate": 10.62, "rate_type": "fixed", "establishment_fee": 295,
     "features": ["No early repayment fee", "Weekly/fortnightly/monthly repayments"]},
    {"product_code": "PL-SEC-002", "name": "Secured Personal Loan",
     "loan_type_code": "personal", "category_code": "general", "secured": True,
     "min_amount": 10000, "max_amount": 100000, "min_term_months": 12, "max_term_months": 84,
     "interest_rate": 6.49, "comparison_rate": 7.11, "rate_type": "fixed", "establishment_fee": 395,
     "features": ["Lower rate for secured asset", "Redraw available"]},
    {"product_code": "HL-VAR-010", "name": "Flexible Variable Home Loan",
     "loan_type_code": "home", "category_code": "owner_occupied", "secured": True,
     "min_amount": 100000, "max_amount": 2000000, "min_term_months": 60, "max_term_months": 360,
     "interest_rate": 5.94, "comparison_rate": 6.02, "rate_type": "variable", "establishment_fee": 600,
     "max_lvr": 95, "features": ["Offset account", "Unlimited extra repayments", "Redraw"]},
    {"product_code": "HL-FIX-011", "name": "3 Year Fixed Home Loan",
     "loan_type_code": "home", "category_code": "owner_occupied", "secured": True,
     "min_amount": 100000, "max_amount": 1500000, "min_term_months": 120, "max_term_months": 360,
     "interest_rate": 5.59, "comparison_rate": 5.98, "rate_type": "fixed", "establishment_fee": 600,
     "max_lvr": 90, "features": ["Rate certainty for 3 years", "Extra repayments capped at $10k/yr"]},
    {"product_code": "VL-NEW-020", "name": "New Vehicle Loan",
     "loan_type_code": "personal", "category_code": "vehicle", "secured": True,
     "min_amount": 10000, "max_amount": 150000, "min_term_months": 12, "max_term_months": 84,
     "interest_rate": 6.89, "comparison_rate": 7.44, "rate_type": "fixed", "establishment_fee": 350,
     "features": ["Vehicles up to 3 years old", "Balloon payment option"]},
    {"product_code": "VL-USED-021", "name": "Used Vehicle Loan",
     "loan_type_code": "personal", "category_code": "vehicle", "secured": True,
     "min_amount": 8000, "max_amount": 100000, "min_term_months": 12, "max_term_months": 72,
     "interest_rate": 8.49, "comparison_rate": 9.05, "rate_type": "fixed", "establishment_fee": 350,
     "features": ["Vehicles up to 12 years old at end of term"]},
    {"product_code": "BL-TERM-030", "name": "Business Term Loan",
     "loan_type_code": "business", "category_code": "term", "secured": True,
     "min_amount": 20000, "max_amount": 1000000, "min_term_months": 12, "max_term_months": 180,
     "interest_rate": 8.25, "comparison_rate": 8.90, "rate_type": "variable", "establishment_fee": 750,
     "features": ["Interest-only period available", "Property or business assets as security"]},
    {"product_code": "IL-PROP-040", "name": "Investment Property Loan",
     "loan_type_code": "home", "category_code": "investment", "secured": True,
     "min_amount": 150000, "max_amount": 2000000, "min_term_months": 120, "max_term_months": 360,
     "interest_rate": 6.34, "comparison_rate": 6.48, "rate_type": "variable", "establishment_fee": 700,
     "max_lvr": 90, "features": ["Interest-only up to 5 years", "Offset account"]},
]

DOCUMENT_TYPES = [
    {"code": "primary_photo_id", "name": "Primary photo ID"},
    {"code": "proof_of_address", "name": "Proof of address"},
    {"code": "payslip_or_contract", "name": "Payslip or employment contract"},
    {"code": "payslip_or_tax_return", "name": "Payslip or tax return"},
    {"code": "bank_statements", "name": "Bank statements"},
    {"code": "tax_return", "name": "Tax return"},
    {"code": "loan_statement", "name": "Loan statement"},
    {"code": "contract_of_sale", "name": "Contract of sale"},
    {"code": "business_registration", "name": "Business registration (ABN/ACN)"},
    {"code": "financial_statements", "name": "Financial statements (P&L, balance sheet)"},
    {"code": "ato_position", "name": "ATO position statement"},
]

DOCUMENT_REQUIREMENTS = [
    {"loan_type_code": "personal", "category_code": "general", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "personal", "category_code": "general", "document_type_code": "proof_of_address"},
    {"loan_type_code": "personal", "category_code": "general", "document_type_code": "payslip_or_contract"},
    {"loan_type_code": "personal", "category_code": "general", "document_type_code": "bank_statements"},

    {"loan_type_code": "personal", "category_code": "vehicle", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "personal", "category_code": "vehicle", "document_type_code": "proof_of_address"},
    {"loan_type_code": "personal", "category_code": "vehicle", "document_type_code": "payslip_or_contract"},
    {"loan_type_code": "personal", "category_code": "vehicle", "document_type_code": "bank_statements"},
    {"loan_type_code": "personal", "category_code": "vehicle", "document_type_code": "contract_of_sale"},

    {"loan_type_code": "home", "category_code": "owner_occupied", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "home", "category_code": "owner_occupied", "document_type_code": "proof_of_address"},
    {"loan_type_code": "home", "category_code": "owner_occupied", "document_type_code": "payslip_or_tax_return"},
    {"loan_type_code": "home", "category_code": "owner_occupied", "document_type_code": "bank_statements"},

    {"loan_type_code": "home", "category_code": "investment", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "home", "category_code": "investment", "document_type_code": "proof_of_address"},
    {"loan_type_code": "home", "category_code": "investment", "document_type_code": "payslip_or_tax_return"},
    {"loan_type_code": "home", "category_code": "investment", "document_type_code": "bank_statements"},
    {"loan_type_code": "home", "category_code": "investment", "document_type_code": "loan_statement"},

    {"loan_type_code": "business", "category_code": "term", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "business", "category_code": "term", "document_type_code": "business_registration"},
    {"loan_type_code": "business", "category_code": "term", "document_type_code": "bank_statements"},
    {"loan_type_code": "business", "category_code": "term", "document_type_code": "tax_return"},
    {"loan_type_code": "business", "category_code": "term", "document_type_code": "financial_statements"},

    {"loan_type_code": "business", "category_code": "overdraft", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "business", "category_code": "overdraft", "document_type_code": "business_registration"},
    {"loan_type_code": "business", "category_code": "overdraft", "document_type_code": "bank_statements"},
    {"loan_type_code": "business", "category_code": "overdraft", "document_type_code": "tax_return"},

    {"loan_type_code": "business", "category_code": "equipment", "document_type_code": "primary_photo_id"},
    {"loan_type_code": "business", "category_code": "equipment", "document_type_code": "business_registration"},
    {"loan_type_code": "business", "category_code": "equipment", "document_type_code": "bank_statements"},
    {"loan_type_code": "business", "category_code": "equipment", "document_type_code": "tax_return"},
    {"loan_type_code": "business", "category_code": "equipment", "document_type_code": "contract_of_sale"},
]
async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for lt in LOAN_TYPES:
            session.add(LoanType(**lt))
        await session.flush()
        
        for c in CATEGORIES:
            session.add(Category(**c))
        await session.flush()
        
        for p in PRODUCTS:
            session.add(Product(**p))
        
        for dt in DOCUMENT_TYPES:
            session.add(DocumentType(**dt))
        await session.flush()

        for dr in DOCUMENT_REQUIREMENTS:
            session.add(DocumentRequirement(**dr))
        
        await session.commit()

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())