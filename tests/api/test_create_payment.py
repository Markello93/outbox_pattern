import uuid

import sqlalchemy

from app.core.database import models
from tests.api.conftest import PAYMENTS_URL, api_headers, payment_create_payload
from tests.helpers import get_one_or_none


async def test_create_payment_returns_202(api_client, test_database):
    idempotency_key = uuid.uuid4()

    response = await api_client.post(
        PAYMENTS_URL,
        json=payment_create_payload(),
        headers=api_headers(idempotency_key=idempotency_key),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == models.PaymentStatusType.PENDING
    assert "payment_id" in body
    assert "created_at" in body

    payment = await get_one_or_none(
        test_database,
        models.Payment,
        id=uuid.UUID(body["payment_id"]),
    )
    assert payment is not None
    assert payment.idempotency_key == idempotency_key

    async for session in test_database.get_session():
        outbox_count = await session.scalar(
            sqlalchemy.select(sqlalchemy.func.count()).select_from(models.OutboxEvent)
        )
    assert outbox_count == 1


async def test_create_payment_idempotency_returns_same_payment(api_client):
    idempotency_key = uuid.uuid4()
    headers = api_headers(idempotency_key=idempotency_key)
    payload = payment_create_payload()

    first_response = await api_client.post(PAYMENTS_URL, json=payload, headers=headers)
    second_response = await api_client.post(PAYMENTS_URL, json=payload, headers=headers)

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert first_response.json()["payment_id"] == second_response.json()["payment_id"]


async def test_create_payment_requires_api_key(api_client):
    response = await api_client.post(
        PAYMENTS_URL,
        json=payment_create_payload(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    assert response.status_code == 401


async def test_create_payment_validation_error(api_client):
    response = await api_client.post(
        PAYMENTS_URL,
        json=payment_create_payload(amount="-1"),
        headers=api_headers(idempotency_key=uuid.uuid4()),
    )

    assert response.status_code == 422
