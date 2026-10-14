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
        "taxpayer_name": "text", "abn": "text", "financial_year": "text",
        "total_business_income": "currency", "net_business_income": "currency",
        "taxable_income": "currency",
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
        "business_name": "text", "abn": "text", "acn": "text", "entity_type": "text",
        "abn_status": "text", "abn_active_from": "date", "gst_registered_from": "date",
    },
    "financial_statements": {
        "entity_name": "text", "financial_year_end": "date",
        "revenue": "currency", "net_profit_before_tax": "currency",
        "interest_expense": "currency", "depreciation_amortisation": "currency",
        "current_assets": "currency", "current_liabilities": "currency",
        "total_assets": "currency", "total_liabilities": "currency", "total_equity": "currency",
        "prior_year_revenue": "currency", "prior_year_net_profit_before_tax": "currency",
        "two_years_prior_revenue": "currency", "two_years_prior_net_profit_before_tax": "currency",
    },
    "ato_position": {
        "entity_name": "text", "abn": "text", "statement_date": "date",
        "outstanding_amount": "currency", "overdue_amount": "currency",
        "payment_plan_status": "text", "overdue_lodgments": "text",
    },
    "entity_documents": {
        "entity_name": "text", "document_kind": "text", "date_executed": "date",
        "trustee_name": "text", "parties_or_directors": "text",
    },
}

FIELD_GUIDANCE = {
    "tax_return": {
        "total_business_income": "Total business income (gross) for the year shown on the return",
        "net_business_income": "Net income or loss from business; a loss is a negative number",
    },
    "business_registration": {
        "entity_type": "As shown, e.g. Individual/Sole Trader, Partnership, Australian Private Company, Discretionary Trust",
        "abn_status": "Active or Cancelled, as shown",
        "abn_active_from": "The date the ABN became active",
    },
    "financial_statements": {
        "financial_year_end": "The end date of the most recent year reported",
        "revenue": "Total sales or revenue for the most recent year",
        "net_profit_before_tax": "Net profit before income tax for the most recent year; a loss is a negative number",
        "interest_expense": "Interest or finance costs for the most recent year",
        "depreciation_amortisation": "Depreciation plus amortisation for the most recent year",
        "current_assets": "Total current assets on the most recent balance sheet",
        "current_liabilities": "Total current liabilities on the most recent balance sheet",
        "total_liabilities": "Total liabilities on the most recent balance sheet",
        "total_equity": "Total equity on the most recent balance sheet; negative if shown as a deficiency",
        "prior_year_revenue": "Revenue in the comparative column for the year before, only if shown",
        "prior_year_net_profit_before_tax": "Net profit before tax for the year before, only if shown",
        "two_years_prior_revenue": "Revenue for two years before the most recent year, only if shown",
        "two_years_prior_net_profit_before_tax": "Net profit before tax for two years before, only if shown",
    },
    "ato_position": {
        "outstanding_amount": "Total balance owed to the ATO across all accounts; 0 if nil; negative if in credit",
        "overdue_amount": "Amount past its due date; 0 if nil",
        "payment_plan_status": "Whether a payment plan is in place and its status, as shown",
        "overdue_lodgments": "Any overdue lodgments listed (BAS, returns); 'none' if the statement shows none",
    },
    "entity_documents": {
        "document_kind": "One of: trust_deed, partnership_agreement, company_constitution, other",
        "entity_name": "The name of the trust, partnership or company the document constitutes",
        "trustee_name": "The trustee named, for a trust deed",
        "parties_or_directors": "Partners, directors or appointors named, comma separated",
    },
}
