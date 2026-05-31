import uuid
from enum import StrEnum

import pydantic


class PaymentWebhookStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PaymentWebhookPayload(pydantic.BaseModel):
    payment_id: uuid.UUID
    status: PaymentWebhookStatus
