import uuid

import sqlalchemy
from sqlalchemy import func

from app.core import database
from app.core.database import models


class PaymentConsumerRepository:
    def __init__(self, db: database.Database):
        self._db = db

    async def get_payment(self, payment_id: uuid.UUID) -> sqlalchemy.RowMapping | None:
        query = sqlalchemy.select(
            models.Payment.id,
            models.Payment.status,
            models.Payment.webhook_url,
        ).where(models.Payment.id == payment_id)
        async for session in self._db.get_session():
            result = await session.execute(query)
        return result.mappings().first()

    async def mark_succeeded(self, payment_id: uuid.UUID) -> None:
        query = (
            sqlalchemy.update(models.Payment)
            .where(models.Payment.id == payment_id)
            .values(
                status=models.PaymentStatusType.SUCCEEDED,
                processed_at=func.now(),
                last_error=None,
            )
        )
        async for session in self._db.get_session():
            await session.execute(query)
            await session.commit()

    async def mark_failed(self, payment_id: uuid.UUID, error_message: str) -> None:
        query = (
            sqlalchemy.update(models.Payment)
            .where(models.Payment.id == payment_id)
            .values(
                status=models.PaymentStatusType.FAILED,
                processed_at=func.now(),
                last_error=error_message[:1000],
            )
        )
        async for session in self._db.get_session():
            await session.execute(query)
            await session.commit()
