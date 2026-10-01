from __future__ import annotations

from typing import TYPE_CHECKING

from shared.db_base import Base

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from admin.models.supplier_products import SupplierProduct


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    barcode: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True,
        index=True
    )

    show_in_deals: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    category: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="products"
    )

    store_products: Mapped[list["StoreProduct"]] = relationship(
        "StoreProduct",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    supplier_products: Mapped[list["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="product"
    )