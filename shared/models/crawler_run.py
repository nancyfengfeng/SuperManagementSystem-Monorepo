from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)

from sqlalchemy.orm import Mapped, mapped_column

from shared.db_base import Base
from shared.models.mixins import TimestampMixin


class CrawlerRun(TimestampMixin, Base):

    __tablename__ = "crawler_runs"


    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )


    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id"),
        nullable=False,
        index=True
    )


    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )


    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )


    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )


    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )