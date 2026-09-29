from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin

class SupplierProduct(TimestampMixin, Base):
    __tablename__ = "supplier_products"

    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "supplier_product_code",
            name="uq_supplier_product_code"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"),
        nullable=True,
        index=True
    )

    supplier_product_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    barcode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="supplier_products"
    )

    product: Mapped["Product | None"] = relationship(
        "Product",
        back_populates="supplier_products"
    )

    prices: Mapped[list["SupplierPriceHistory"]] = relationship(
        "SupplierPriceHistory",
        back_populates="supplier_product"
    )