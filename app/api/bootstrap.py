import punq

from app.api.payment.v1 import repository, service
from app.core import database, settings


def resolve_resources(config: settings.ApiSettings) -> punq.Container:
    container = punq.Container()

    container.register(service=settings.ApiSettings, instance=config)
    container.register(
        service=database.Database,
        factory=database.Database,
        scope=punq.Scope.singleton,
        config=config.database,
    )
    container.register(
        service=repository.PaymentRepository,
        factory=repository.PaymentRepository,
        scope=punq.Scope.singleton,
    )
    container.register(
        service=service.PaymentService,
        factory=service.PaymentService,
        scope=punq.Scope.singleton,
    )
    return container
