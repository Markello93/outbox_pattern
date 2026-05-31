from typing import TypeVar

import fastapi
from fastapi import security

from app.core import settings

T = TypeVar("T")

_api_key_header = security.APIKeyHeader(name="X-API-Key", auto_error=False)


def inject(cls: type[T]):
    def dependency(request: fastapi.Request) -> T:
        return request.app.state.container.resolve(cls)

    return fastapi.Depends(dependency)


async def verify_api_key(
    api_key: str | None = fastapi.Security(_api_key_header),
    config: settings.ApiSettings = inject(settings.ApiSettings),
) -> None:
    if api_key != config.api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
