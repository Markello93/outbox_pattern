import logging
import typing
import uuid

import httpx
from faststream.rabbit import RabbitMessage
from faststream.rabbit.schemas import Channel

from app.consumers.payment import errors, service
from app.core import settings
from app.core.messaging import RabbitBroker, topology
from app.core.messaging.schemas import PaymentCreatedMessage

logger = logging.getLogger(__name__)


def get_main_queue_reject_count(msg: RabbitMessage) -> int:
    """Обработка количества reject сообщений."""
    x_death = msg.headers.get("x-death") or []
    reject_count = 0

    for entry in x_death:
        queue_name = entry.get("queue")
        reject_reason = entry.get("reason")
        if queue_name != topology.payments.consumer_queue:
            continue
        if reject_reason != "rejected":
            continue

        reject_count += int(entry.get("count", 0))

    return reject_count


class PaymentConsumer:
    def __init__(
        self,
        rabbit: RabbitBroker,
        consumer_service: service.PaymentConsumerService,
        config: settings.PaymentConsumerSettings,
    ):
        self._rabbit = rabbit
        self._service = consumer_service
        self._config = config

        self._business_exchange = topology.business_exchange()
        self._dlx_exchange = topology.dlx_exchange()
        self._dlq_queue = topology.dlq_queue()
        self._retry_queue = topology.retry_queue(
            ttl_ms=int(config.queue_retry_ttl_seconds * 1000),
        )
        self._queue = topology.main_queue()

        self._rabbit.broker.subscriber(
            self._queue,
            exchange=self._business_exchange,
            channel=Channel(prefetch_count=config.prefetch_count),
            no_ack=True,
        )(self._consume)

    async def setup(self) -> None:
        business = await self._rabbit.broker.declare_exchange(self._business_exchange)
        dlx = await self._rabbit.broker.declare_exchange(self._dlx_exchange)
        dlq = await self._rabbit.broker.declare_queue(self._dlq_queue)
        await self._rabbit.broker.declare_queue(self._retry_queue)
        main = await self._rabbit.broker.declare_queue(self._queue)
        await main.bind(business, routing_key=topology.payments.routing_key)
        await dlq.bind(dlx)

    async def _move_to_dlq(
        self,
        payload: typing.Mapping[str, typing.Any],
        msg: RabbitMessage,
        *,
        payment_id: uuid.UUID | None,
        reason: str,
    ) -> None:
        logger.warning(
            "Moving message to DLQ reason=%s message_id=%s payment_id=%s x_death_rejects=%s",
            reason,
            msg.message_id,
            payment_id,
            get_main_queue_reject_count(msg),
        )
        await self._rabbit.broker.publish(
            message=dict(payload),
            exchange=topology.payments.dlx,
            message_id=msg.message_id,
            correlation_id=str(payment_id) if payment_id else None,
            persist=True,
        )
        await msg.ack()

    async def _schedule_queue_retry(
        self,
        msg: RabbitMessage,
        *,
        payment_id: uuid.UUID | None,
        reject_count: int,
        reason: str,
    ) -> None:
        logger.warning(
            "Queue retry scheduled reason=%s message_id=%s payment_id=%s "
            "attempt=%s/%s ttl=%ss x_death_rejects=%s",
            reason,
            msg.message_id,
            payment_id,
            reject_count + 1,
            self._config.max_queue_delivery_attempts,
            self._config.queue_retry_ttl_seconds,
            reject_count,
        )
        await msg.reject(requeue=False)

    async def _handle_retryable(
        self,
        payload: typing.Mapping[str, typing.Any],
        msg: RabbitMessage,
        *,
        payment_id: uuid.UUID | None,
        reason: str,
        exc: Exception,
    ) -> None:
        reject_count = get_main_queue_reject_count(msg)
        if reject_count + 1 >= self._config.max_queue_delivery_attempts:
            await self._move_to_dlq(
                payload,
                msg,
                payment_id=payment_id,
                reason=f"{reason}; exhausted queue attempts: {exc!r}",
            )
            return
        await self._schedule_queue_retry(
            msg,
            payment_id=payment_id,
            reject_count=reject_count,
            reason=f"{reason}: {exc!r}",
        )

    async def _consume(self, body: PaymentCreatedMessage, msg: RabbitMessage) -> None:
        payload = body.model_dump(mode="json")
        try:
            await self._service.handle_message(payment_id=body.payment_id)
        except httpx.HTTPError as exc:
            await self._handle_retryable(
                payload,
                msg,
                payment_id=body.payment_id,
                reason="webhook delivery failed",
                exc=exc,
            )
        except errors.PaymentDlqError as exc:
            await self._move_to_dlq(
                payload,
                msg,
                payment_id=exc.payment_id,
                reason=str(exc),
            )
