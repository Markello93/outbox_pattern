import taskiq
import taskiq_redis
from taskiq import schedule_sources

from app.core import settings


class TaskBroker:
    def __init__(self, config: settings.TaskBrokerSettings):
        self._config = config
        self._broker = taskiq_redis.RedisStreamBroker(config.dsn.unicode_string()).with_middlewares(
            taskiq.PrometheusMiddleware(server_addr="0.0.0.0", server_port=8000),
        )

    @property
    def broker(self) -> taskiq_redis.RedisStreamBroker:
        return self._broker


class TaskScheduler:
    def __init__(self, config: settings.TaskBrokerSettings, broker: TaskBroker):
        self._config = config
        self._broker = broker.broker
        self._schedule_source = taskiq_redis.ListRedisScheduleSource(
            self._config.dsn.unicode_string(),
            prefix="payments_tasks",
        )
        self._scheduler = taskiq.TaskiqScheduler(
            broker=self._broker,
            sources=[self._schedule_source, schedule_sources.LabelScheduleSource(self._broker)],
        )

    @property
    def scheduler(self) -> taskiq.TaskiqScheduler:
        return self._scheduler
