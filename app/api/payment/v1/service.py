import uuid

from app.api.payment.v1 import repository, schemas
from app.core.database import models
from app.core.messaging import topology


class PaymentService:
    def __init__(self, payments_repository: repository.PaymentRepository):
        self._repository = payments_repository

    async def create_payment(
        self,
        idempotency_key: uuid.UUID,
        request: schemas.PaymentCreateRequest,
    ) -> models.Payment:
        return await self._repository.create_with_outbox(
            idempotency_key=idempotency_key,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            metadata=request.metadata,
            webhook_url=str(request.webhook_url),
            event_type=topology.payments.routing_key,
        )

    async def get_payment(self, payment_id: uuid.UUID) -> models.Payment | None:
        return await self._repository.get_by_id(payment_id=payment_id)
