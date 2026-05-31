import datetime
import decimal
import typing
import uuid

import pydantic

from app.core.database import models


class PaymentCreateRequest(pydantic.BaseModel):
    amount: decimal.Decimal = pydantic.Field(gt=0, max_digits=14, decimal_places=2)
    currency: models.Currency
    description: str = pydantic.Field(min_length=1, max_length=1024)
    metadata: dict[str, typing.Any] = pydantic.Field(default_factory=dict)
    webhook_url: pydantic.HttpUrl


class PaymentCreateResponse(pydantic.BaseModel):
    payment_id: uuid.UUID
    status: models.PaymentStatusType
    created_at: datetime.datetime


class PaymentDetailResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    payment_id: uuid.UUID = pydantic.Field(validation_alias="id")
    amount: decimal.Decimal
    currency: models.Currency
    description: str
    metadata: dict[str, typing.Any] = pydantic.Field(validation_alias="payment_metadata")
    status: models.PaymentStatusType
    idempotency_key: uuid.UUID
    webhook_url: str
    created_at: datetime.datetime
    processed_at: datetime.datetime | None
    last_error: str | None
