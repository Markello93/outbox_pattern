import typing
import uuid

import pydantic


class ClaimedOutboxEvent(pydantic.BaseModel):
    id: uuid.UUID
    event_type: str
    payload: dict[str, typing.Any]
    attempts: int
