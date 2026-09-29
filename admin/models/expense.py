from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint
)
from sqlalchemy.orm import relationship

from shared.db_base import Base

from datetime import datetime, timezone

# =========================
# 支出主表
# =========================
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    supplier_id = Column(Integer, index=True)

    total_amount = Column(Float, nullable=False)

    date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=True)

    payment_status = Column(
        String(20),
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    payments = relationship(
        "ExpensePayment",
        back_populates="expense",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "payment_status IN ('pending','partial','paid')",
            name="ck_expense_payment_status"
        ),
    )

# =========================
# 支付拆分表
# =========================
class ExpensePayment(Base):
    __tablename__ = "expense_payments"

    id = Column(Integer, primary_key=True)

    expense_id = Column(
        Integer,
        ForeignKey(
            "expenses.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    method = Column(String, nullable=False)  # cash / card / sinpe / caja
    amount = Column(Float)

    # 反向关系
    expense = relationship("Expense", back_populates="payments")

    __table_args__ = (
        CheckConstraint(
            "method IN ('cash','card','sinpe','caja')",
            name="ck_expense_method_valid"
        ),
    )