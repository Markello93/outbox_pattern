import datetime
import typing

import fastapi
import pydantic

app = fastapi.FastAPI(title="Webhook Mock", version="1.0.0")


class WebhookReceivedResponse(pydantic.BaseModel):
    status: str = "received"
    received_at: datetime.datetime


@app.post("/webhook", response_model=WebhookReceivedResponse)
async def receive_webhook(_payload: dict[str, typing.Any]) -> WebhookReceivedResponse:
    return WebhookReceivedResponse(received_at=datetime.datetime.now())
