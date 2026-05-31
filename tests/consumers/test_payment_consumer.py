import uuid

import httpx
import pydantic
import pytest
import respx

from app.consumers.payment.consumer import get_main_queue_reject_count
from app.core.database import models
from app.core.messaging import topology
from app.core.messaging.schemas import PaymentCreatedMessage
from tests.consumers.conftest import WEBHOOK_URL, rabbit_message_with_reject_count
from tests.helpers import get_one_or_none


def payment_message(payment_id: uuid.UUID) -> PaymentCreatedMessage:
    return PaymentCreatedMessage(payment_id=payment_id)


@pytest.mark.usefixtures("gateway_success")
async def test_consume_success_marks_payment_succeeded(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
    create_payment_in_db,
):
    payment = await create_payment_in_db()

    with respx.mock(assert_all_called=True) as router:
        router.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))
        await payment_consumer._consume(payment_message(payment.id), mock_rabbit_message)

    updated_payment = await get_one_or_none(
        payment_consumer._service._payments_repository._db,
        models.Payment,
        id=payment.id,
    )
    assert updated_payment.status == models.PaymentStatusType.SUCCEEDED
    assert updated_payment.processed_at is not None
    mock_rabbit.broker.publish.assert_not_awaited()
    mock_rabbit_message.reject.assert_not_awaited()


@pytest.mark.usefixtures("gateway_failure")
async def test_consume_gateway_failure_marks_payment_failed(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
    create_payment_in_db,
):
    payment = await create_payment_in_db()

    with respx.mock(assert_all_called=True) as router:
        router.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))
        await payment_consumer._consume(payment_message(payment.id), mock_rabbit_message)

    updated_payment = await get_one_or_none(
        payment_consumer._service._payments_repository._db,
        models.Payment,
        id=payment.id,
    )
    assert updated_payment.status == models.PaymentStatusType.FAILED
    assert updated_payment.last_error == "Gateway processing simulation failed"
    mock_rabbit.broker.publish.assert_not_awaited()
    mock_rabbit_message.reject.assert_not_awaited()


async def test_consume_already_processed_is_idempotent(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
    create_payment_in_db,
):
    payment = await create_payment_in_db(status=models.PaymentStatusType.SUCCEEDED)

    with respx.mock:
        await payment_consumer._consume(payment_message(payment.id), mock_rabbit_message)

    mock_rabbit.broker.publish.assert_not_awaited()
    mock_rabbit_message.reject.assert_not_awaited()


def test_payment_created_payload_requires_payment_id():
    with pytest.raises(pydantic.ValidationError):
        PaymentCreatedMessage.model_validate({"amount": "100.00"})


def test_payment_created_payload_requires_valid_uuid():
    with pytest.raises(pydantic.ValidationError):
        PaymentCreatedMessage.model_validate({"payment_id": "not-a-uuid"})


async def test_consume_payment_not_found_moves_to_dlq(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
):
    missing_payment_id = uuid.uuid4()

    await payment_consumer._consume(payment_message(missing_payment_id), mock_rabbit_message)

    mock_rabbit.broker.publish.assert_awaited_once_with(
        message=payment_message(missing_payment_id).model_dump(mode="json"),
        exchange=topology.payments.dlx,
        message_id=mock_rabbit_message.message_id,
        correlation_id=str(missing_payment_id),
        persist=True,
    )
    mock_rabbit_message.ack.assert_awaited_once()
    mock_rabbit_message.reject.assert_not_awaited()


@pytest.mark.usefixtures("gateway_success")
async def test_consume_webhook_server_error_schedules_retry(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
    create_payment_in_db,
):
    payment = await create_payment_in_db()

    with respx.mock(assert_all_called=True) as router:
        webhook_route = router.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))
        await payment_consumer._consume(payment_message(payment.id), mock_rabbit_message)

    assert webhook_route.call_count == 3
    mock_rabbit_message.reject.assert_awaited_once_with(requeue=False)
    mock_rabbit.broker.publish.assert_not_awaited()
    mock_rabbit_message.ack.assert_not_awaited()

    updated_payment = await get_one_or_none(
        payment_consumer._service._payments_repository._db,
        models.Payment,
        id=payment.id,
    )
    assert updated_payment.status == models.PaymentStatusType.PENDING


@pytest.mark.usefixtures("gateway_success")
async def test_consume_webhook_bad_request_schedules_retry(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
    create_payment_in_db,
):
    payment = await create_payment_in_db()

    with respx.mock(assert_all_called=True) as router:
        webhook_route = router.post(WEBHOOK_URL).mock(return_value=httpx.Response(400))
        await payment_consumer._consume(payment_message(payment.id), mock_rabbit_message)

    assert webhook_route.call_count == 3
    mock_rabbit_message.reject.assert_awaited_once_with(requeue=False)
    mock_rabbit.broker.publish.assert_not_awaited()


@pytest.mark.usefixtures("gateway_success")
async def test_consume_webhook_timeout_schedules_retry(
    payment_consumer,
    mock_rabbit,
    mock_rabbit_message,
    create_payment_in_db,
):
    payment = await create_payment_in_db()

    with respx.mock(assert_all_called=True) as router:
        webhook_route = router.post(WEBHOOK_URL).mock(side_effect=httpx.ReadTimeout("timeout"))
        await payment_consumer._consume(payment_message(payment.id), mock_rabbit_message)

    assert webhook_route.call_count == 3
    mock_rabbit_message.reject.assert_awaited_once_with(requeue=False)
    mock_rabbit.broker.publish.assert_not_awaited()
    mock_rabbit_message.ack.assert_not_awaited()


@pytest.mark.usefixtures("gateway_success")
async def test_consume_webhook_error_before_exhausted_attempts_rejects_only(
    payment_consumer,
    mock_rabbit,
    create_payment_in_db,
):
    payment = await create_payment_in_db()
    message = rabbit_message_with_reject_count(reject_count=0)

    with respx.mock(assert_all_called=True) as router:
        router.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))
        await payment_consumer._consume(payment_message(payment.id), message)

    message.reject.assert_awaited_once_with(requeue=False)
    mock_rabbit.broker.publish.assert_not_awaited()
    message.ack.assert_not_awaited()


@pytest.mark.usefixtures("gateway_success")
async def test_consume_webhook_error_exhausted_attempts_moves_to_dlq(
    payment_consumer,
    mock_rabbit,
    create_payment_in_db,
):
    payment = await create_payment_in_db()
    message = rabbit_message_with_reject_count(reject_count=2)

    with respx.mock(assert_all_called=True) as router:
        router.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))
        await payment_consumer._consume(payment_message(payment.id), message)

    mock_rabbit.broker.publish.assert_awaited_once()
    publish_kwargs = mock_rabbit.broker.publish.await_args.kwargs
    assert publish_kwargs["exchange"] == topology.payments.dlx
    assert publish_kwargs["correlation_id"] == str(payment.id)
    message.ack.assert_awaited_once()
    message.reject.assert_not_awaited()


def test_get_main_queue_reject_count_sums_rejects_from_main_queue():
    message = rabbit_message_with_reject_count(reject_count=2)
    message.headers["x-death"].append(
        {
            "queue": topology.payments.retry_queue,
            "reason": "rejected",
            "count": 5,
        }
    )

    assert get_main_queue_reject_count(message) == 2


def test_get_main_queue_reject_count_without_x_death():
    message = rabbit_message_with_reject_count(reject_count=0)
    message.headers = {}

    assert get_main_queue_reject_count(message) == 0
