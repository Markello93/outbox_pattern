import abc

from app.core import settings
from app.core.worker import task_broker


class BaseWorker(abc.ABC):
    def __init__(self, broker: task_broker.TaskBroker, config: settings.BaseJobSettings):
        self._broker = broker.broker
        self._config = config
        if self._config.run:
            self._register_schedules()

    def _register_schedules(self):
        @self._broker.task(
            task_name=self._config.name,
            schedule=[{"cron": self._config.cron_expression}],
        )
        async def processing_task():
            await self.job()

    @abc.abstractmethod
    async def job(self) -> None:
        raise NotImplementedError
