from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin

class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=False,
        index=True
    )

    invoice_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    invoice_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    invoice_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True
    )

    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="invoices"
    )

    price_records: Mapped[list["SupplierPriceHistory"]] = relationship(
        "SupplierPriceHistory",
        back_populates="invoice"
    )

