import asyncio
import logging

import uvicorn
from faststream import FastStream
from faststream.asgi import AsgiResponse, get

from app.consumers import bootstrap
from app.consumers.payment import PaymentConsumer
from app.core import database, settings
from app.core.messaging import RabbitBroker, make_metrics

logger = logging.getLogger(__name__)


def create_app(config: settings.ConsumerSettings | None = None):
    config = config or settings.ConsumerSettings()
    resources = bootstrap.resolve_resources(config=config)
    rabbit = resources.resolve(RabbitBroker)
    consumer = resources.resolve(PaymentConsumer)
    db = resources.resolve(database.Database)

    fs_app = FastStream(rabbit.broker)

    @fs_app.after_startup
    async def setup_consumer() -> None:
        await consumer.setup()

    @get
    async def health(_scope) -> AsgiResponse:
        try:
            if await rabbit.broker.ping(config.consumer_rabbit_ping_timeout):
                await db.ping()
                return AsgiResponse(b"", status_code=204)
        except Exception:
            logger.exception("Health check failed")
        return AsgiResponse(b"", status_code=500)

    return fs_app.as_asgi(
        asgi_routes=[
            ("/health", health),
            ("/metrics", make_metrics(rabbit)),
        ],
    )


app = create_app()


async def run() -> None:
    config = settings.ConsumerSettings()
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.consumer_health_port,
        log_level=config.logging_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(run())
