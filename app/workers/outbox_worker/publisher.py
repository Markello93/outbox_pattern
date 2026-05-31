from app.core.messaging import RabbitBroker
from app.core.messaging import schemas as messaging_schemas
from app.core.messaging import topology
from app.workers.outbox_worker import schemas


class OutboxPublisher:
    def __init__(self, broker: RabbitBroker):
        self._broker = broker

    async def publish_event(self, event: schemas.ClaimedOutboxEvent) -> None:
        message = messaging_schemas.PaymentCreatedMessage.model_validate(event.payload)
        await self._broker.broker.publish(
            message=message.model_dump(mode="json"),
            exchange=topology.payments.exchange,
            routing_key=event.event_type,
            message_id=str(event.id),
            correlation_id=str(message.payment_id),
            persist=True,
        )
