import punq

from app.consumers.payment import PaymentConsumer, PaymentConsumerRepository, PaymentConsumerService
from app.core import database, settings
from app.core.messaging import RabbitBroker


def resolve_resources(config: settings.ConsumerSettings) -> punq.Container:
    container = punq.Container()
    container.register(
        service=database.Database,
        factory=database.Database,
        scope=punq.Scope.singleton,
        config=config.database,
    )
    container.register(
        service=RabbitBroker,
        factory=RabbitBroker,
        scope=punq.Scope.singleton,
        config=config.rabbit,
    )
    container.register(
        service=PaymentConsumerRepository,
        factory=PaymentConsumerRepository,
        scope=punq.Scope.singleton,
    )
    container.register(
        service=PaymentConsumerService,
        factory=PaymentConsumerService,
        scope=punq.Scope.singleton,
        config=config.payment_consumer,
    )
    container.register(
        service=PaymentConsumer,
        factory=PaymentConsumer,
        scope=punq.Scope.singleton,
        config=config.payment_consumer,
    )
    return container
