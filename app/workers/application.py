import taskiq
import taskiq_redis
from taskiq import TaskiqEvents, TaskiqState

from app.core import database, settings
from app.core.messaging import RabbitBroker
from app.core.worker import task_broker
from app.workers import outbox_worker


class WorkerScheduler:
    def __init__(
        self,
        config: settings.WorkersSettings,
        db: database.Database,
        rabbit: RabbitBroker,
        outbox_worker_job: outbox_worker.worker.OutboxWorker,
        scheduler: task_broker.TaskScheduler,
    ):
        self._config = config
        self._db = db
        self._rabbit = rabbit
        self._outbox_worker_job = outbox_worker_job
        self._scheduler = scheduler.scheduler
        self._setup_lifecycle_hooks()

    def _setup_lifecycle_hooks(self):
        @self._scheduler.broker.on_event(TaskiqEvents.WORKER_STARTUP)
        async def startup_event(state: TaskiqState) -> None:  # noqa: ARG001
            await self._rabbit.connect()

        @self._scheduler.broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
        async def shutdown_event(state: TaskiqState) -> None:  # noqa: ARG001
            await self._rabbit.disconnect()

    @property
    def app(self) -> taskiq.TaskiqScheduler:
        return self._scheduler

    @property
    def broker(self) -> taskiq_redis.RedisStreamBroker:
        return self._scheduler.broker
