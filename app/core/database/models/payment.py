import decimal
import enum
import uuid

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from app.core import database
from app.core.database import mixins


class Currency(enum.StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatusType(enum.StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Payment(database.Base, mixins.PrimaryKeyMixin, mixins.CreatedAtMixin, mixins.ProcessingStateMixin):
    __tablename__ = "payments"

    amount: orm.Mapped[decimal.Decimal] = orm.mapped_column(
        sqlalchemy.Numeric(14, 2),
        comment="Сумма платежа",
        nullable=False,
    )
    description: orm.Mapped[str] = orm.mapped_column(
        sqlalchemy.String(1024),
        comment="Описание",
        nullable=False,
    )
    currency: orm.Mapped[Currency] = orm.mapped_column(
        sqlalchemy.Enum(Currency, name="payment_currency_enum"),
        nullable=False,
    )
    status: orm.Mapped[PaymentStatusType] = orm.mapped_column(
        sqlalchemy.Enum(PaymentStatusType, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatusType.PENDING,
    )
    payment_metadata: orm.Mapped[dict] = orm.mapped_column(
        "metadata", postgresql.JSONB, nullable=False, default=dict
    )
    idempotency_key: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sqlalchemy.UUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    webhook_url: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(1024), nullable=False)
