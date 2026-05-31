from faststream.asgi import AsgiResponse, get
from faststream.asgi.types import ASGIApp, Scope
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.messaging.broker import RabbitBroker


def make_metrics(rabbit: RabbitBroker) -> ASGIApp:
    @get
    async def metrics(_scope: Scope) -> AsgiResponse:
        payload = generate_latest(rabbit.registry)
        return AsgiResponse(payload, 200, headers={"content-type": CONTENT_TYPE_LATEST})

    return metrics
