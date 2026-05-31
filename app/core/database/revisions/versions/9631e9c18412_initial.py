"""initial

Revision ID: 9631e9c18412
Revises:
Create Date: 2026-05-30 14:31:12.929828

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9631e9c18412"
down_revision = None
branch_labels = None
depends_on = None

outbox_status_enum = sa.Enum(
    "PENDING",
    "PROCESSING",
    "PUBLISHED",
    "FAILED",
    "DEAD",
    name="outboxstatustype",
)
payment_currency_enum = sa.Enum("RUB", "USD", "EUR", name="payment_currency_enum")
payment_status_enum = sa.Enum("PENDING", "SUCCEEDED", "FAILED", name="payment_status_enum")


def upgrade() -> None:
    outbox_status_enum.create(op.get_bind(), checkfirst=True)
    payment_currency_enum.create(op.get_bind(), checkfirst=True)
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "outbox_events",
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="outboxstatustype", create_type=False),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        "ix_outbox_status_next_retry_created",
        "outbox_events",
        ["status", "next_retry_at", "created_at"],
        unique=False,
    )

    op.create_table(
        "payments",
        sa.Column(
            "amount",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            comment="Сумма платежа",
        ),
        sa.Column("description", sa.String(length=1024), nullable=False, comment="Описание"),
        sa.Column(
            "currency",
            postgresql.ENUM(name="payment_currency_enum", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="payment_status_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.UUID(), nullable=False),
        sa.Column("webhook_url", sa.String(length=1024), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_payments_idempotency_key")),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_index("ix_outbox_status_next_retry_created", table_name="outbox_events")
    op.drop_table("outbox_events")

    sa.Enum(name="outboxstatustype").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="payment_currency_enum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="payment_status_enum").drop(op.get_bind(), checkfirst=False)
