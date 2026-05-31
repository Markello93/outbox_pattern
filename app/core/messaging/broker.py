import logging

import prometheus_client
from faststream import rabbit as faststream_rabbit
from faststream.rabbit import prometheus

from app.core import settings

logger = logging.getLogger(__name__)


class RabbitBroker:
    """FastStream RabbitBroker и prometheus registry."""

    def __init__(self, config: settings.RabbitServerSettings):
        self._registry = prometheus_client.CollectorRegistry()
        self._broker = faststream_rabbit.RabbitBroker(
            f"amqp://{config.username}:{config.password}@{config.host}:{config.port}/{config.vhost}",
            middlewares=(prometheus.RabbitPrometheusMiddleware(registry=self._registry),),
        )

    @property
    def broker(self):
        return self._broker

    @property
    def registry(self):
        return self._registry

    async def connect(self) -> None:
        logger.info("Connecting to RabbitMQ...")
        await self._broker.start()

    async def disconnect(self) -> None:
        logger.info("Closing RabbitMQ connection...")
        await self._broker.close()
