from sqlalchemy import (
    Boolean,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    # 你们内部使用的简称 / 备注名称
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # XML 里面 Emisor.Nombre 的正式公司名称
    legal_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True
    )

    # XML 里面 Emisor.Identificacion.Numero
    # 以后用这个作为供应商匹配的主要依据
    tax_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    supplier_products: Mapped[list["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="supplier"
    )

    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="supplier"
    )