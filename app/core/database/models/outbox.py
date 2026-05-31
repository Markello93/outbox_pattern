import enum

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from app.core import database
from app.core.database import mixins


class OutboxStatusType(enum.StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DEAD = "DEAD"


class OutboxEvent(
    database.Base,
    mixins.PrimaryKeyMixin,
    mixins.TimestampMixin,
    mixins.ProcessingStateMixin,
):
    __tablename__ = "outbox_events"
    event_type: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(255), nullable=False)
    payload: orm.Mapped[dict] = orm.mapped_column(postgresql.JSONB, nullable=False)
    status: orm.Mapped[OutboxStatusType] = orm.mapped_column(
        sqlalchemy.Enum(OutboxStatusType),
        nullable=False,
        default=OutboxStatusType.PENDING,
    )
    attempts: orm.Mapped[int] = orm.mapped_column(sqlalchemy.Integer, nullable=False, default=0)
    next_retry_at: orm.Mapped[sqlalchemy.DateTime] = orm.mapped_column(sqlalchemy.DateTime, nullable=True)
    __table_args__ = (
        sqlalchemy.Index(
            "ix_outbox_status_next_retry_created",
            "status",
            "next_retry_at",
            "created_at",
        ),
    )
