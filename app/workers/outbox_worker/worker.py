import logging

from app.core import settings
from app.core.worker import base_worker, task_broker
from app.workers.outbox_worker import service

logger = logging.getLogger(__name__)


class OutboxWorker(base_worker.BaseWorker):
    def __init__(
        self,
        config: settings.OutboxWorkerSettings,
        events_service: service.OutboxService,
        task_broker: task_broker.TaskBroker,
    ):
        super().__init__(config=config, broker=task_broker)
        self._service = events_service

    async def job(self):
        logger.info(f"{self.__class__.__name__} job started.")
        await self._service.main()
        logger.info(f"{self.__class__.__name__} job completed.")
