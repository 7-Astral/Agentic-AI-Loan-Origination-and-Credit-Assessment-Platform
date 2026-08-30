# LOAN_TYPES = [
#     {"code": "personal", "name": "Personal Loan",
#      "description": "Unsecured or secured loan for personal use, including vehicles."},
#     {"code": "home", "name": "Home Loan",
#      "description": "Loan to buy, refinance, or invest in residential property."},
#     {"code": "business", "name": "Business Loan",
#      "description": "Term finance for business purposes."},
# ]

# # Subtypes within each loan_type.

# CATEGORIES = {
#     "personal": ["general", "vehicle"],
#     "home": ["owner_occupied", "investment"],
#     "business": ["term", "overdraft", "equipment"],
# }

# PRODUCTS = [
#     {
#         "product_code": "PL-STD-001", "name": "Standard Personal Loan",
#         "loan_type": "personal", "category": "general", "secured": False,
#         "min_amount": 5000, "max_amount": 50000,
#         "min_term_months": 12, "max_term_months": 84,
#         "interest_rate": 9.99, "comparison_rate": 10.62,
#         "rate_type": "fixed", "establishment_fee": 295,
#         "features": ["No early repayment fee", "Weekly/fortnightly/monthly repayments"],
#     },
#     {
#         "product_code": "PL-SEC-002", "name": "Secured Personal Loan",
#         "loan_type": "personal", "category": "general", "secured": True,
#         "min_amount": 10000, "max_amount": 100000,
#         "min_term_months": 12, "max_term_months": 84,
#         "interest_rate": 6.49, "comparison_rate": 7.11,
#         "rate_type": "fixed", "establishment_fee": 395,
#         "features": ["Lower rate for secured asset", "Redraw available"],
#     },
#     {
#         "product_code": "HL-VAR-010", "name": "Flexible Variable Home Loan",
#         "loan_type": "home", "category": "owner_occupied", "secured": True,
#         "min_amount": 100000, "max_amount": 2000000,
#         "min_term_months": 60, "max_term_months": 360,
#         "interest_rate": 5.94, "comparison_rate": 6.02,
#         "rate_type": "variable", "establishment_fee": 600,
#         "max_lvr": 95,
#         "features": ["Offset account", "Unlimited extra repayments", "Redraw"],
#     },
#     {
#         "product_code": "HL-FIX-011", "name": "3 Year Fixed Home Loan",
#         "loan_type": "home", "category": "owner_occupied", "secured": True,
#         "min_amount": 100000, "max_amount": 1500000,
#         "min_term_months": 120, "max_term_months": 360,
#         "interest_rate": 5.59, "comparison_rate": 5.98,
#         "rate_type": "fixed", "establishment_fee": 600,
#         "max_lvr": 90,
#         "features": ["Rate certainty for 3 years", "Extra repayments capped at $10k/yr"],
#     },
#     {
#         "product_code": "VL-NEW-020", "name": "New Vehicle Loan",
#         "loan_type": "personal", "category": "vehicle", "secured": True,
#         "min_amount": 10000, "max_amount": 150000,
#         "min_term_months": 12, "max_term_months": 84,
#         "interest_rate": 6.89, "comparison_rate": 7.44,
#         "rate_type": "fixed", "establishment_fee": 350,
#         "features": ["Vehicles up to 3 years old", "Balloon payment option"],
#     },
#     {
#         "product_code": "VL-USED-021", "name": "Used Vehicle Loan",
#         "loan_type": "personal", "category": "vehicle", "secured": True,
#         "min_amount": 8000, "max_amount": 100000,
#         "min_term_months": 12, "max_term_months": 72,
#         "interest_rate": 8.49, "comparison_rate": 9.05,
#         "rate_type": "fixed", "establishment_fee": 350,
#         "features": ["Vehicles up to 12 years old at end of term"],
#     },
#     {
#         "product_code": "BL-TERM-030", "name": "Business Term Loan",
#         "loan_type": "business", "category": "term", "secured": True,
#         "min_amount": 20000, "max_amount": 1000000,
#         "min_term_months": 12, "max_term_months": 180,
#         "interest_rate": 8.25, "comparison_rate": 8.90,
#         "rate_type": "variable", "establishment_fee": 750,
#         "features": ["Interest-only period available", "Property or business assets as security"],
#     },
#     {
#         "product_code": "IL-PROP-040", "name": "Investment Property Loan",
#         "loan_type": "home", "category": "investment", "secured": True,
#         "min_amount": 150000, "max_amount": 2000000,
#         "min_term_months": 120, "max_term_months": 360,
#         "interest_rate": 6.34, "comparison_rate": 6.48,
#         "rate_type": "variable", "establishment_fee": 700,
#         "max_lvr": 90,
#         "features": ["Interest-only up to 5 years", "Offset account"],
#     },
# ]