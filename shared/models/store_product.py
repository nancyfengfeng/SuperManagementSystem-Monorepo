from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin


class StoreProduct(TimestampMixin, Base):
    __tablename__ = "store_products"

    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_store_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)

    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False, index=True)

    original_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="store_products")

    store: Mapped["Store"] = relationship("Store", back_populates="store_products")

    promotions: Mapped[list["StoreProductPromotion"]] = relationship("StoreProductPromotion", back_populates="store_product", cascade="all, delete-orphan")