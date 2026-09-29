from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin


class SupplierPriceHistory(TimestampMixin, Base):
    __tablename__ = "supplier_price_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    supplier_product_id: Mapped[int] = mapped_column(
        ForeignKey("supplier_products.id"),
        nullable=False,
        index=True
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id"),
        nullable=False,
        index=True
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 5),
        nullable=False
    )

    discount_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(18, 5),
        default=Decimal("0"),
        nullable=False
    )

    net_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 5),
        nullable=False
    )

    tax_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 4),
        nullable=True
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="CRC",
        nullable=False
    )

    supplier_product: Mapped["SupplierProduct"] = relationship(
        "SupplierProduct",
        back_populates="prices"
    )

    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="price_records"
    )