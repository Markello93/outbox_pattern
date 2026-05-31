import datetime
import typing
import uuid

import sqlalchemy
from sqlalchemy import func

from app.core import database
from app.core.database import models


class OutboxRepository:
    def __init__(self, db: database.Database):
        self._db = db

    async def claim_events(
        self,
        limit: int,
        stale_after_seconds: int = 60,
    ) -> typing.Sequence[sqlalchemy.RowMapping]:
        """Захват батча: PENDING, FAILED к retry и stale PROCESSING."""
        stale_before = func.now() - datetime.timedelta(seconds=stale_after_seconds)

        claimable_events_cte = (
            sqlalchemy.select(models.OutboxEvent.id)
            .where(
                sqlalchemy.or_(
                    models.OutboxEvent.status == models.OutboxStatusType.PENDING,
                    sqlalchemy.and_(
                        models.OutboxEvent.status == models.OutboxStatusType.FAILED,
                        sqlalchemy.or_(
                            models.OutboxEvent.next_retry_at.is_(None),
                            models.OutboxEvent.next_retry_at <= func.now(),
                        ),
                    ),
                    sqlalchemy.and_(
                        models.OutboxEvent.status == models.OutboxStatusType.PROCESSING,
                        models.OutboxEvent.updated_at < stale_before,
                    ),
                )
            )
            .order_by(sqlalchemy.asc(models.OutboxEvent.created_at))
            .limit(limit)
            .with_for_update(skip_locked=True)
            .cte("claimable_events")
        )

        claim_query = (
            sqlalchemy.update(models.OutboxEvent)
            .where(
                models.OutboxEvent.id.in_(
                    sqlalchemy.select(claimable_events_cte.c.id),
                ),
            )
            .values(
                status=models.OutboxStatusType.PROCESSING,
                updated_at=func.now(),
            )
            .returning(
                models.OutboxEvent.id,
                models.OutboxEvent.event_type,
                models.OutboxEvent.payload,
                models.OutboxEvent.attempts,
            )
            .add_cte(claimable_events_cte)
        )

        async for session in self._db.get_session():
            result = await session.execute(claim_query)
            await session.commit()
        return result.mappings().all()

    async def mark_published(self, outbox_id: uuid.UUID) -> None:
        query = (
            sqlalchemy.update(models.OutboxEvent)
            .where(models.OutboxEvent.id == outbox_id)
            .values(
                status=models.OutboxStatusType.PUBLISHED,
                processed_at=func.now(),
                last_error=None,
            )
        )
        async for session in self._db.get_session():
            await session.execute(query)
            await session.commit()

    async def mark_failed(
        self,
        outbox_id: uuid.UUID,
        attempts: int,
        error_message: str,
        retry_delay_seconds: int,
    ) -> None:
        query = (
            sqlalchemy.update(models.OutboxEvent)
            .where(models.OutboxEvent.id == outbox_id)
            .values(
                status=models.OutboxStatusType.FAILED,
                attempts=attempts,
                last_error=error_message[:1000],
                next_retry_at=func.now() + datetime.timedelta(seconds=retry_delay_seconds),
            )
        )
        async for session in self._db.get_session():
            await session.execute(query)
            await session.commit()

    async def mark_dead(
        self,
        outbox_id: uuid.UUID,
        attempts: int,
        error_message: str,
    ) -> None:
        query = (
            sqlalchemy.update(models.OutboxEvent)
            .where(models.OutboxEvent.id == outbox_id)
            .values(
                status=models.OutboxStatusType.DEAD,
                attempts=attempts,
                last_error=error_message[:1000],
                next_retry_at=None,
                processed_at=func.now(),
            )
        )
        async for session in self._db.get_session():
            await session.execute(query)
            await session.commit()
