import asyncio
import logging

from app.core import settings
from app.workers.outbox_worker import publisher, repository, schemas

logger = logging.getLogger(__name__)


class OutboxService:
    def __init__(
        self,
        events_repository: repository.OutboxRepository,
        config: settings.OutboxWorkerSettings,
        publisher: publisher.OutboxPublisher,
    ):
        self._repository = events_repository
        self._config = config
        self._publisher = publisher

    async def main(self) -> None:
        claimed_events = await self._repository.claim_events(limit=self._config.events_limit)
        if not claimed_events:
            return

        events = [schemas.ClaimedOutboxEvent(**event) for event in claimed_events]
        await asyncio.gather(*(self._handle_event(event) for event in events))

    async def _handle_event(self, event: schemas.ClaimedOutboxEvent) -> None:
        try:
            await self._publisher.publish_event(event=event)
            await self._repository.mark_published(outbox_id=event.id)
        except asyncio.CancelledError as exc:
            await self._mark_publish_failure(event, exc)
        except Exception as exc:  # noqa: BLE001
            await self._mark_publish_failure(event, exc)

    async def _mark_publish_failure(self, event: schemas.ClaimedOutboxEvent, exc: BaseException) -> None:
        attempts = event.attempts + 1
        error_message = f"{type(exc).__name__}: {exc!r}"

        if attempts >= self._config.max_attempts:
            logger.warning(
                "Outbox publish failed, event %s marked DEAD (attempt %s/%s): %s",
                event.id,
                attempts,
                self._config.max_attempts,
                error_message,
            )
            await self._repository.mark_dead(
                outbox_id=event.id,
                attempts=attempts,
                error_message=error_message,
            )
            return

        retry_delay_seconds = self._retry_delay_seconds(attempts)
        logger.warning(
            "Outbox publish failed, event %s marked FAILED (attempt %s/%s), retry in %ss: %s",
            event.id,
            attempts,
            self._config.max_attempts,
            retry_delay_seconds,
            error_message,
        )
        await self._repository.mark_failed(
            outbox_id=event.id,
            attempts=attempts,
            error_message=error_message,
            retry_delay_seconds=retry_delay_seconds,
        )

    def _retry_delay_seconds(self, attempts: int) -> int:
        return self._config.retry_base_delay_seconds * (2 ** (attempts - 1))
