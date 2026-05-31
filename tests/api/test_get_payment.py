import uuid

from tests.api.conftest import PAYMENTS_URL, api_headers, payment_create_payload


async def test_get_payment_returns_details(api_client):
    idempotency_key = uuid.uuid4()
    create_response = await api_client.post(
        PAYMENTS_URL,
        json=payment_create_payload(description="Order payment"),
        headers=api_headers(idempotency_key=idempotency_key),
    )
    payment_id = create_response.json()["payment_id"]

    response = await api_client.get(
        f"{PAYMENTS_URL}/{payment_id}",
        headers=api_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["payment_id"] == payment_id
    assert body["description"] == "Order payment"
    assert body["currency"] == "RUB"
    assert body["idempotency_key"] == str(idempotency_key)
    assert body["status"] == "PENDING"
    assert body["last_error"] is None


async def test_get_payment_not_found(api_client):
    response = await api_client.get(
        f"{PAYMENTS_URL}/{uuid.uuid4()}",
        headers=api_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"


async def test_get_payment_requires_api_key(api_client):
    response = await api_client.get(f"{PAYMENTS_URL}/{uuid.uuid4()}")

    assert response.status_code == 401
