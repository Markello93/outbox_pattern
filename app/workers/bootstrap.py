import punq

from app.core import database, settings
from app.core.messaging import RabbitBroker
from app.core.worker import task_broker
from app.workers import outbox_worker


def resolve_resources(config: settings.WorkersSettings) -> punq.Container:
    container = punq.Container()
    container.register(
        service=database.Database,
        factory=database.Database,
        scope=punq.Scope.singleton,
        config=config.database,
    )
    container.register(
        service=task_broker.TaskBroker,
        factory=task_broker.TaskBroker,
        scope=punq.Scope.singleton,
        config=config.task_broker,
    )
    container.register(
        service=task_broker.TaskScheduler,
        factory=task_broker.TaskScheduler,
        scope=punq.Scope.singleton,
        config=config.task_broker,
    )
    container.register(
        service=RabbitBroker,
        factory=RabbitBroker,
        scope=punq.Scope.singleton,
        config=config.rabbit,
    )
    container.register(
        service=outbox_worker.publisher.OutboxPublisher,
        factory=outbox_worker.publisher.OutboxPublisher,
        scope=punq.Scope.singleton,
    )
    container.register(
        service=outbox_worker.repository.OutboxRepository,
        factory=outbox_worker.repository.OutboxRepository,
        scope=punq.Scope.singleton,
    )
    container.register(
        service=outbox_worker.service.OutboxService,
        factory=outbox_worker.service.OutboxService,
        scope=punq.Scope.singleton,
        config=config.outbox_worker,
    )
    container.register(
        service=outbox_worker.worker.OutboxWorker,
        factory=outbox_worker.worker.OutboxWorker,
        scope=punq.Scope.singleton,
        config=config.outbox_worker,
    )
    return container
