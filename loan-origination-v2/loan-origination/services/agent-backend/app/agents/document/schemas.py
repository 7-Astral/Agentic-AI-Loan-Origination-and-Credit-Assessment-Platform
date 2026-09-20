EXTRACTION_SCHEMAS = {
    "primary_photo_id": {
        "full_name": "text", "date_of_birth": "date",
        "document_number": "text", "expiry_date": "date",
    },
    "proof_of_address": {
        "name_on_document": "text", "address": "text", "document_date": "date",
    },
    "payslip_or_contract": {
        "employee_name": "text", "employer_name": "text",
        "gross_pay_this_period": "currency",
        "pay_period_start": "date", "pay_period_end": "date",
        "pay_frequency": "text",
    },
    "payslip_or_tax_return": {
        "applicant_name": "text", "gross_annual_income": "currency",
        "financial_year": "text",
    },
    "bank_statements": {
        "account_holder_name": "text",
        "statement_period_start": "date", "statement_period_end": "date",
        "closing_balance": "currency",
        "transactions": "transaction_list",
    },
    "tax_return": {
        "applicant_name": "text", "abn": "text",
        "financial_year": "text", "taxable_income": "currency",
    },
    "loan_statement": {
        "lender_name": "text", "outstanding_balance": "currency",
        "monthly_repayment": "currency",
    },
    "contract_of_sale": {
        "buyer_name": "text", "seller_type": "text", "item_description": "text",
        "purchase_price": "currency", "sale_date": "date",
    },
    "business_registration": {
        "business_name": "text", "abn": "text", "acn": "text",
        "status": "text", "registration_date": "date",
    },
    "financial_statements": {
        "statement_period": "text", "revenue": "currency", "cogs": "currency",
        "operating_expenses": "currency", "ebitda": "currency",
        "net_profit": "currency", "total_assets": "currency", "total_liabilities": "currency",
    },
    "ato_position": {
        "outstanding_amount": "currency",
        "payment_plan_status": "text", "lodgment_status": "text",
    },
}