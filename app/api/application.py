import contextlib
import typing

import fastapi

from app.api import bootstrap
from app.api.payment.v1 import routes
from app.core import database, settings


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> typing.AsyncIterator[None]:
    yield
    await app.state.container.resolve(database.Database).shutdown()


def create_app() -> fastapi.FastAPI:
    container = bootstrap.resolve_resources(config=settings.ApiSettings())
    app = fastapi.FastAPI(
        title="Payments API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.container = container
    app.include_router(routes.router)
    return app
