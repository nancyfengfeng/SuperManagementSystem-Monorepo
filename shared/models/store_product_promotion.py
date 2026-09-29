from datetime import datetime

from sqlalchemy import Integer, Numeric, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin


class StoreProductPromotion(TimestampMixin, Base):
    __tablename__ = "store_product_promotions"

    __table_args__ = (
        UniqueConstraint("store_product_id", "quantity", name="uq_store_product_promotion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    store_product_id: Mapped[int] = mapped_column(ForeignKey("store_products.id"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    store_product = relationship("StoreProduct", back_populates="promotions")