import uuid
from unittest import mock

import pytest

from app.core.database import models
from app.core.messaging import topology
from app.core.messaging.schemas import PaymentCreatedMessage
from app.workers import bootstrap as workers_bootstrap
from app.workers.outbox_worker import publisher as outbox_publisher
from app.workers.outbox_worker import service, worker


@pytest.fixture
def container_workers(test_config):
    return workers_bootstrap.resolve_resources(test_config)


@pytest.fixture
def mock_publisher(container_workers):
    publisher_mock = mock.AsyncMock(spec=outbox_publisher.OutboxPublisher)
    container_workers.register(outbox_publisher.OutboxPublisher, instance=publisher_mock)
    return publisher_mock


@pytest.fixture
def outbox_service(container_workers, mock_publisher):
    _ = mock_publisher
    return container_workers.resolve(service.OutboxService)


@pytest.fixture
def outbox_worker(container_workers, mock_publisher):
    _ = mock_publisher
    return container_workers.resolve(worker.OutboxWorker)


@pytest.fixture
async def create_outbox_event_in_db(test_database):
    async def _create(
        *,
        payment_id: uuid.UUID | None = None,
        status: models.OutboxStatusType = models.OutboxStatusType.PENDING,
        attempts: int = 0,
        event_type: str = topology.payments.routing_key,
    ) -> models.OutboxEvent:
        resolved_payment_id = payment_id or uuid.uuid4()
        event = models.OutboxEvent(
            event_type=event_type,
            payload=PaymentCreatedMessage(payment_id=resolved_payment_id).model_dump(mode="json"),
            status=status,
            attempts=attempts,
        )
        async for session in test_database.get_session():
            session.add(event)
            await session.commit()
            await session.refresh(event)
        return event

    return _create
