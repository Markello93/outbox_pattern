import decimal
import uuid
from unittest import mock

import pytest

from app.consumers.payment import gateway
from app.consumers.payment.consumer import PaymentConsumer
from app.consumers.payment.repository import PaymentConsumerRepository
from app.consumers.payment.service import PaymentConsumerService
from app.core import settings
from app.core.database import models
from app.core.messaging import RabbitBroker, topology

WEBHOOK_URL = "http://webhook.test/webhook"


def rabbit_message_with_reject_count(*, reject_count: int = 0):
    message = mock.AsyncMock()
    message.message_id = "test-message-id"
    message.headers = {
        "x-death": [
            {
                "queue": topology.payments.consumer_queue,
                "reason": "rejected",
                "count": reject_count,
            }
        ]
    }
    message.ack = mock.AsyncMock()
    message.reject = mock.AsyncMock()
    return message


@pytest.fixture
def consumer_config() -> settings.PaymentConsumerSettings:
    return settings.PaymentConsumerSettings(
        gateway_delay_min_seconds=0.001,
        gateway_delay_max_seconds=0.001,
        gateway_success_rate=1.0,
        webhook_timeout_seconds=5.0,
        queue_retry_ttl_seconds=30,
        max_queue_delivery_attempts=3,
        prefetch_count=1,
    )


@pytest.fixture
def mock_rabbit_message():
    return rabbit_message_with_reject_count(reject_count=0)


@pytest.fixture
def mock_rabbit():
    rabbit = mock.Mock(spec=RabbitBroker)
    rabbit.broker = mock.AsyncMock()
    rabbit.broker.publish = mock.AsyncMock()
    rabbit.broker.subscriber = mock.Mock(return_value=lambda handler: handler)
    return rabbit


@pytest.fixture
def consumer_service(test_database, consumer_config):
    repository = PaymentConsumerRepository(db=test_database)
    return PaymentConsumerService(payments_repository=repository, config=consumer_config)


@pytest.fixture
def payment_consumer(mock_rabbit, consumer_service, consumer_config):
    return PaymentConsumer(
        rabbit=mock_rabbit,
        consumer_service=consumer_service,
        config=consumer_config,
    )


@pytest.fixture
async def create_payment_in_db(test_database):
    async def _create(
        *,
        status: models.PaymentStatusType = models.PaymentStatusType.PENDING,
        webhook_url: str = WEBHOOK_URL,
    ) -> models.Payment:
        payment = models.Payment(
            amount=decimal.Decimal("100.00"),
            currency=models.Currency.RUB,
            description="test payment",
            payment_metadata={"order_id": "1"},
            idempotency_key=uuid.uuid4(),
            webhook_url=webhook_url,
            status=status,
        )
        async for session in test_database.get_session():
            session.add(payment)
            await session.commit()
        return payment

    return _create


@pytest.fixture
def gateway_success(monkeypatch):
    async def _emulate(_config: settings.PaymentConsumerSettings) -> bool:
        return True

    monkeypatch.setattr(gateway, "emulate_payment_gateway", _emulate)


@pytest.fixture
def gateway_failure(monkeypatch):
    async def _emulate(_config: settings.PaymentConsumerSettings) -> bool:
        return False

    monkeypatch.setattr(gateway, "emulate_payment_gateway", _emulate)
