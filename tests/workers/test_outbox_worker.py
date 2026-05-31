from app.core.database import models
from tests.helpers import get_one_or_none


async def test_publish_outbox_event_success(
    test_database,
    outbox_service,
    mock_publisher,
    create_outbox_event_in_db,
):
    event = await create_outbox_event_in_db()

    await outbox_service.main()

    mock_publisher.publish_event.assert_awaited_once()

    updated_event = await get_one_or_none(test_database, models.OutboxEvent, id=event.id)
    assert updated_event.status == models.OutboxStatusType.PUBLISHED
    assert updated_event.processed_at is not None
    assert updated_event.last_error is None


async def test_publish_outbox_event_failure_marks_failed(
    test_database,
    outbox_service,
    mock_publisher,
    create_outbox_event_in_db,
):
    event = await create_outbox_event_in_db()
    mock_publisher.publish_event.side_effect = RuntimeError("broker unavailable")

    await outbox_service.main()

    updated_event = await get_one_or_none(test_database, models.OutboxEvent, id=event.id)
    assert updated_event.status == models.OutboxStatusType.FAILED
    assert updated_event.attempts == 1
    assert updated_event.next_retry_at is not None
    assert "RuntimeError" in updated_event.last_error


async def test_publish_outbox_event_dead_after_max_attempts(
    test_database,
    outbox_service,
    mock_publisher,
    create_outbox_event_in_db,
):
    event = await create_outbox_event_in_db(attempts=2)
    mock_publisher.publish_event.side_effect = RuntimeError("broker unavailable")

    await outbox_service.main()

    updated_event = await get_one_or_none(test_database, models.OutboxEvent, id=event.id)
    assert updated_event.status == models.OutboxStatusType.DEAD
    assert updated_event.attempts == 3
    assert updated_event.next_retry_at is None


async def test_outbox_worker_job_delegates_to_service(
    outbox_worker,
    mock_publisher,
    create_outbox_event_in_db,
):
    await create_outbox_event_in_db()

    await outbox_worker.job()

    mock_publisher.publish_event.assert_awaited_once()
