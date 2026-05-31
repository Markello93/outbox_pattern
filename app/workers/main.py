import typing

import punq

from app.core import settings
from app.workers import application, bootstrap

config = settings.WorkersSettings()
resources = bootstrap.resolve_resources(config=config)
resources.register(
    service=application.WorkerScheduler,
    factory=application.WorkerScheduler,
    scope=punq.Scope.singleton,
    config=config,
)
app = typing.cast(application.WorkerScheduler, resources.resolve(application.WorkerScheduler))

scheduler = app.app
broker = app.broker
