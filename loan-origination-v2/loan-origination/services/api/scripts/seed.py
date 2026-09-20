"""Seed default data so you can log in immediately after the first migration.

Run with:
    docker compose exec api python -m scripts.seed
    (or, running natively:  python -m scripts.seed   from inside services/api)

Safe to re-run — it checks for existing rows before inserting, so it won't
create duplicates.

Default logins created (all passwords follow the same pattern — change them
before this ever goes near production):
    admin@bank.com    / Admin@123      (role: admin, platform-wide)
    manager@bank.com  / Manager@123    (role: staff, Credit Manager — can manage
                                         First National Bank's staff/products/policies)
    officer@bank.com  / Officer@123    (role: staff, Loan Officer — restricted,
                                         demonstrates permission gating)
    customer@bank.com / Customer@123   (role: customer)

Also seeds First National Bank's approval ladder (bank_positions): Loan Officer
-> Credit Manager -> CFO -> CEO -> Board, each with an approval limit, used by
the auto-approve/escalate routing in app/core/lending_logic.py.
"""
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.bank import Bank
from app.models.bank_position import BankPosition
from app.models.enums import LoanType, UserRole
from app.models.lending_policy import LendingPolicy
from app.models.loan_product import LoanProduct
from app.models.user import User


async def get_or_create(db, model, defaults: dict, **lookup):
    result = await db.execute(select(model).filter_by(**lookup))
    instance = result.scalar_one_or_none()
    if instance:
        return instance, False
    instance = model(**lookup, **defaults)
    db.add(instance)
    await db.flush()
    return instance, True


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        bank, created = await get_or_create(
            db,
            Bank,
            code="FNB001",
            defaults={"name": "First National Bank", "contact_email": "contact@fnb.example"},
        )
        print(f"Bank: {bank.name} ({'created' if created else 'already existed'})")

        admin_user, created = await get_or_create(
            db,
            User,
            email="admin@bank.com",
            defaults={
                "password_hash": hash_password("Admin@123"),
                "full_name": "Platform Admin",
                "role": UserRole.ADMIN.value,
            },
        )
        print(f"Admin user: admin@bank.com ({'created' if created else 'already existed'})")

        ladder = [
            {"title": "Loan Officer", "rank": 1, "max_approval_amount": 50_000, "can_manage_staff": False, "can_manage_products": False},
            {"title": "Credit Manager", "rank": 2, "max_approval_amount": 250_000, "can_manage_staff": True, "can_manage_products": True},
            {"title": "CFO", "rank": 3, "max_approval_amount": 1_000_000, "can_manage_staff": True, "can_manage_products": True},
            {"title": "CEO", "rank": 4, "max_approval_amount": 5_000_000, "can_manage_staff": True, "can_manage_products": True},
            {"title": "Board", "rank": 5, "max_approval_amount": None, "can_manage_staff": True, "can_manage_products": True},
        ]
        positions = {}
        for level in ladder:
            title = level.pop("title")
            position, created = await get_or_create(db, BankPosition, bank_id=bank.id, title=title, defaults=level)
            positions[title] = position
            print(f"Position: {title} ({'created' if created else 'already existed'})")

        manager_user, created = await get_or_create(
            db,
            User,
            email="manager@bank.com",
            defaults={
                "password_hash": hash_password("Manager@123"),
                "full_name": "Casey Manager",
                "role": UserRole.STAFF.value,
                "bank_id": bank.id,
                "position_id": positions["Credit Manager"].id,
            },
        )
        print(f"Staff user: manager@bank.com — Credit Manager ({'created' if created else 'already existed'})")

        officer_user, created = await get_or_create(
            db,
            User,
            email="officer@bank.com",
            defaults={
                "password_hash": hash_password("Officer@123"),
                "full_name": "Riley Officer",
                "role": UserRole.STAFF.value,
                "bank_id": bank.id,
                "position_id": positions["Loan Officer"].id,
            },
        )
        print(f"Staff user: officer@bank.com — Loan Officer ({'created' if created else 'already existed'})")

        customer_user, created = await get_or_create(
            db,
            User,
            email="customer@bank.com",
            defaults={
                "password_hash": hash_password("Customer@123"),
                "full_name": "Jordan Customer",
                "role": UserRole.CUSTOMER.value,
            },
        )
        print(f"Customer user: customer@bank.com ({'created' if created else 'already existed'})")

        personal, created = await get_or_create(
            db,
            LoanProduct,
            bank_id=bank.id,
            name="Everyday Personal Loan",
            defaults={
                "product_type": LoanType.PERSONAL.value,
                "min_amount": 2000,
                "max_amount": 50000,
                "interest_rate_min": 8.5,
                "interest_rate_max": 15.0,
                "tenure_min_months": 6,
                "tenure_max_months": 60,
                "eligibility_criteria": {"min_credit_score": 600, "min_age": 18},
            },
        )
        print(f"Loan product: {personal.name} ({'created' if created else 'already existed'})")

        business, created = await get_or_create(
            db,
            LoanProduct,
            bank_id=bank.id,
            name="Small Business Growth Loan",
            defaults={
                "product_type": LoanType.BUSINESS.value,
                "min_amount": 10000,
                "max_amount": 500000,
                "interest_rate_min": 10.0,
                "interest_rate_max": 18.0,
                "tenure_min_months": 12,
                "tenure_max_months": 84,
                "eligibility_criteria": {"min_credit_score": 650, "min_years_trading": 1},
            },
        )
        print(f"Loan product: {business.name} ({'created' if created else 'already existed'})")

        home, created = await get_or_create(
            db,
            LoanProduct,
            bank_id=bank.id,
            name="Home Purchase Loan",
            defaults={
                "product_type": LoanType.HOME.value,
                "min_amount": 50000,
                "max_amount": 2000000,
                "interest_rate_min": 6.0,
                "interest_rate_max": 9.0,
                "tenure_min_months": 60,
                "tenure_max_months": 360,
                "eligibility_criteria": {"min_credit_score": 680, "max_dti_ratio": 0.43},
            },
        )
        print(f"Loan product: {home.name} ({'created' if created else 'already existed'})")

        policy, created = await get_or_create(
            db,
            LendingPolicy,
            bank_id=bank.id,
            product_id=personal.id,
            defaults={
                "auto_approval_max_amount": 10000,
                "min_credit_score": 650,
                "max_dti_ratio": 0.40,
                "rules": {"require_all_documents_verified": True},
            },
        )
        print(f"Lending policy for {personal.name} ({'created' if created else 'already existed'})")

        await db.commit()
        print("\nSeed complete. Log in at http://localhost:3000/login with:")
        print("  admin@bank.com    / Admin@123    (platform admin)")
        print("  manager@bank.com  / Manager@123  (Credit Manager — full bank self-service)")
        print("  officer@bank.com  / Officer@123  (Loan Officer — restricted)")
        print("  customer@bank.com / Customer@123")


if __name__ == "__main__":
    asyncio.run(seed())
