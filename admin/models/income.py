from sqlalchemy import Column, Integer, Float, String, Date, DateTime,ForeignKey,CheckConstraint
from sqlalchemy.orm import relationship

from shared.db_base import Base

from datetime import datetime, timezone

class Income(Base):
    __tablename__ = "incomes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)

    date = Column(Date, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    types = relationship(
        "IncomeType",
        back_populates="income",
        cascade="all, delete-orphan"
    )


class IncomeType(Base):
    __tablename__ = "income_types"

    id = Column(Integer, primary_key=True)

    income_id = Column(
        Integer,
        ForeignKey(
            "incomes.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    income_type = Column(String, nullable=False)  # cash/card/sinpe/usd
    amount = Column(Float, nullable=False)

    income = relationship("Income", back_populates="types")

    __table_args__ = (
        CheckConstraint(
            "income_type IN ('cash','card','sinpe')",
            name="ck_income_type_valid"
        ),
    )