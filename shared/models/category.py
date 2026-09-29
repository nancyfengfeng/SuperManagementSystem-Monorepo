from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base
from shared.models.mixins import TimestampMixin

class Category(TimestampMixin,Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    external_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True,
        index=True
    )

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    is_leaf: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    parent: Mapped[Category | None] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children"
    )

    children: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="parent"
    )

    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="category"
    )