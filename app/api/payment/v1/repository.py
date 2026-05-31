import decimal
import typing
import uuid

import sqlalchemy
from sqlalchemy.ext import asyncio as sa_asyncio

from app.core import database
from app.core.database import models
from app.core.messaging.schemas import PaymentCreatedMessage


class PaymentRepository:
    def __init__(self, db: database.Database):
        self._db = db

    async def get_by_id(self, payment_id: uuid.UUID) -> models.Payment | None:
        query = sqlalchemy.select(models.Payment).where(models.Payment.id == payment_id)
        async for session in self._db.get_session():
            result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_with_outbox(
        self,
        *,
        idempotency_key: uuid.UUID,
        amount: decimal.Decimal,
        currency: models.Currency,
        description: str,
        metadata: dict[str, typing.Any],
        webhook_url: str,
        event_type: str,
    ) -> models.Payment:
        """Создание outbox события и платежа в одной транзакции.
        Обработка дубликатов с помощью idempotency_key.
        """
        async for session in self._db.get_session():  # noqa: RET503
            async with session.begin():
                existing = await self._select_by_idempotency_key(session, idempotency_key)
                if existing is not None:
                    return existing

                payment = models.Payment(
                    amount=amount,
                    currency=currency,
                    description=description,
                    payment_metadata=metadata,
                    webhook_url=webhook_url,
                    idempotency_key=idempotency_key,
                    status=models.PaymentStatusType.PENDING,
                )
                session.add(payment)
                await session.flush()

                session.add(
                    models.OutboxEvent(
                        event_type=event_type,
                        payload=PaymentCreatedMessage(payment_id=payment.id).model_dump(mode="json"),
                        status=models.OutboxStatusType.PENDING,
                    )
                )

            await session.refresh(payment)
            return payment

    @staticmethod
    async def _select_by_idempotency_key(
        session: sa_asyncio.AsyncSession,
        idempotency_key: uuid.UUID,
    ) -> models.Payment | None:
        result = await session.execute(
            sqlalchemy.select(models.Payment).where(models.Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()
