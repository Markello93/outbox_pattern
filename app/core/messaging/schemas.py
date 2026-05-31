import uuid

import pydantic


class PaymentCreatedMessage(pydantic.BaseModel):
    payment_id: uuid.UUID
