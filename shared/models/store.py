from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin

class Store(TimestampMixin,Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )

    store_products: Mapped[list["StoreProduct"]] = relationship(
        "StoreProduct",
        back_populates="store"
    )