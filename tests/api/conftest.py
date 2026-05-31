import uuid

import fastapi
import httpx
import pytest

from app.api import bootstrap
from app.api.payment.v1 import routes
from app.core import database, settings

API_KEY = "dev-api-key"
PAYMENTS_URL = "/api/v1/payments"


def api_headers(*, idempotency_key: uuid.UUID | None = None) -> dict[str, str]:
    headers = {"X-API-Key": API_KEY}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = str(idempotency_key)
    return headers


def payment_create_payload(**overrides) -> dict:
    payload = {
        "amount": "100.50",
        "currency": "RUB",
        "description": "Test payment",
        "metadata": {"order_id": "1"},
        "webhook_url": "http://webhook.test/webhook",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
async def api_client(test_database):
    config = settings.ApiSettings()
    container = bootstrap.resolve_resources(config)
    container.register(database.Database, instance=test_database)

    app = fastapi.FastAPI(title="Payments API", version="1.0.0")
    app.state.container = container
    app.include_router(routes.router)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
