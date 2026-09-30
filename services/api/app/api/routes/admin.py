from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_labels import resolve_entity_labels
from app.core.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.bank import Bank
from app.models.bank_position import BankPosition
from app.models.enums import BankStatus, UserRole
from app.models.lending_policy import LendingPolicy
from app.models.loan_application import LoanApplication
from app.models.loan_product import LoanProduct
from app.models.user import User
from app.schemas.admin import (
    AuditLogOut,
    BankOut,
    CreateBankPositionRequest,
    CreateBankRequest,
    CreateStaffRequest,
    DashboardStats,
    LendingPolicyOut,
    LoanProductOut,
)
from app.schemas.auth import UserOut
from app.schemas.bank import BankPositionOut

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN.value))])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    banks = (await db.execute(select(func.count()).select_from(Bank))).scalar_one()
    products = (await db.execute(select(func.count()).select_from(LoanProduct))).scalar_one()
    applications = (await db.execute(select(func.count()).select_from(LoanApplication))).scalar_one()
    return DashboardStats(
        total_users=users,
        total_banks=banks,
        total_loan_products=products,
        total_applications=applications,
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: CreateStaffRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    bank = await db.get(Bank, payload.bank_id)
    if bank is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bank not found")

    if payload.position_id is not None:
        position = await db.get(BankPosition, payload.position_id)
        if position is None or position.bank_id != payload.bank_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position not found for this bank")

    staff = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.STAFF.value,
        bank_id=payload.bank_id,
        position_id=payload.position_id,
    )
    db.add(staff)
    await db.flush()

    db.add(
        AuditLog(
            bank_id=payload.bank_id,
            entity_type="user",
            entity_id=str(staff.id),
            action="staff_created",
            performed_by=admin.id,
            after_state={"email": staff.email, "full_name": staff.full_name, "bank_id": str(payload.bank_id)},
        )
    )
    await db.commit()
    await db.refresh(staff)
    return staff


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    if user_id == str(admin.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")

    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target.is_active:
        target.is_active = False
        db.add(
            AuditLog(
                bank_id=target.bank_id,
                entity_type="user",
                entity_id=str(target.id),
                action="user_deactivated",
                performed_by=admin.id,
                after_state={"email": target.email, "is_active": False},
            )
        )
        await db.commit()
        await db.refresh(target)
    return target


@router.post("/users/{user_id}/reactivate", response_model=UserOut)
async def reactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not target.is_active:
        target.is_active = True
        db.add(
            AuditLog(
                bank_id=target.bank_id,
                entity_type="user",
                entity_id=str(target.id),
                action="user_reactivated",
                performed_by=admin.id,
                after_state={"email": target.email, "is_active": True},
            )
        )
        await db.commit()
        await db.refresh(target)
    return target


@router.get("/banks", response_model=list[BankOut])
async def list_banks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).order_by(Bank.name))
    return result.scalars().all()


@router.post("/banks", response_model=BankOut, status_code=status.HTTP_201_CREATED)
async def create_bank(
    payload: CreateBankRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """Onboards a new bank. There's no separate "bank admin" account type —
    a bank is managed by its own staff, so this also creates a starter
    "Branch Manager" position (unlimited approval, can manage staff and
    products) so there's an immediate answer to "how do I appoint someone
    to run this bank": create the bank here, then add a staff account for
    them (Admin > Users) against this bank with that position."""
    existing = await db.execute(select(Bank).where(Bank.code == payload.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A bank with that code already exists")

    bank = Bank(
        name=payload.name,
        code=payload.code,
        contact_email=payload.contact_email,
        status=BankStatus.ACTIVE.value,
    )
    db.add(bank)
    await db.flush()

    db.add(
        BankPosition(
            bank_id=bank.id,
            title="Branch Manager",
            rank=1,
            max_approval_amount=None,
            can_manage_staff=True,
            can_manage_products=True,
        )
    )

    db.add(
        AuditLog(
            bank_id=bank.id,
            entity_type="bank",
            entity_id=str(bank.id),
            action="bank_created",
            performed_by=admin.id,
            after_state={"name": bank.name, "code": bank.code},
        )
    )
    await db.commit()
    await db.refresh(bank)
    return bank


@router.post("/banks/{bank_id}/deactivate", response_model=BankOut)
async def deactivate_bank(
    bank_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """Flags a bank inactive. Not a hard delete — its staff, products and
    application history all stay intact. Note this is currently a status
    flag only: it isn't yet enforced anywhere (staff at an inactive bank can
    still log in, its products still list) — surfacing/enforcing it
    elsewhere is a natural follow-up, not done here."""
    bank = await db.get(Bank, bank_id)
    if bank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")

    if bank.status != BankStatus.INACTIVE.value:
        bank.status = BankStatus.INACTIVE.value
        db.add(
            AuditLog(
                bank_id=bank.id,
                entity_type="bank",
                entity_id=str(bank.id),
                action="bank_deactivated",
                performed_by=admin.id,
                after_state={"status": bank.status},
            )
        )
        await db.commit()
        await db.refresh(bank)
    return bank


@router.post("/banks/{bank_id}/reactivate", response_model=BankOut)
async def reactivate_bank(
    bank_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    bank = await db.get(Bank, bank_id)
    if bank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")

    if bank.status != BankStatus.ACTIVE.value:
        bank.status = BankStatus.ACTIVE.value
        db.add(
            AuditLog(
                bank_id=bank.id,
                entity_type="bank",
                entity_id=str(bank.id),
                action="bank_reactivated",
                performed_by=admin.id,
                after_state={"status": bank.status},
            )
        )
        await db.commit()
        await db.refresh(bank)
    return bank


@router.get("/banks/{bank_id}/positions", response_model=list[BankPositionOut])
async def list_bank_positions_for_admin(bank_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BankPosition).where(BankPosition.bank_id == bank_id).order_by(BankPosition.rank.asc())
    )
    return result.scalars().all()


@router.post("/banks/{bank_id}/positions", response_model=BankPositionOut, status_code=status.HTTP_201_CREATED)
async def create_bank_position_for_admin(
    bank_id: str,
    payload: CreateBankPositionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """Adds another rung to a bank's approval ladder — e.g. a bank that
    wants more than one manager-level position, or a fuller ladder
    (Loan Officer / Credit Manager / CFO / CEO, as in the seed data)
    instead of just the single starter position create_bank makes."""
    bank = await db.get(Bank, bank_id)
    if bank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")

    position = BankPosition(bank_id=bank.id, **payload.model_dump())
    db.add(position)
    await db.flush()

    db.add(
        AuditLog(
            bank_id=bank.id,
            entity_type="bank_position",
            entity_id=str(position.id),
            action="position_created",
            performed_by=admin.id,
            after_state={"title": position.title, "bank_id": str(bank.id)},
        )
    )
    await db.commit()
    await db.refresh(position)
    return position


@router.get("/loan-products", response_model=list[LoanProductOut])
async def list_loan_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoanProduct).order_by(LoanProduct.name))
    return result.scalars().all()


@router.get("/lending-policies", response_model=list[LendingPolicyOut])
async def list_lending_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LendingPolicy))
    return result.scalars().all()


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))
    logs = result.scalars().all()
    labels = await resolve_entity_labels(db, logs)
    return [
        AuditLogOut.model_validate(log).model_copy(
            update={"entity_label": labels.get((log.entity_type, log.entity_id))}
        )
        for log in logs
    ]
