import logging
import uuid

import httpx

from app.consumers.payment import errors, gateway, repository, schemas
from app.core import settings
from app.core.database import models
from app.core.decorators import async_retry

logger = logging.getLogger(__name__)


class PaymentConsumerService:
    def __init__(
        self,
        payments_repository: repository.PaymentConsumerRepository,
        config: settings.PaymentConsumerSettings,
    ):
        self._payments_repository = payments_repository
        self._config = config
        self._http_client = httpx.AsyncClient(timeout=config.webhook_timeout_seconds)

    async def handle_message(self, *, payment_id: uuid.UUID) -> None:
        payment = await self._payments_repository.get_payment(payment_id=payment_id)
        if payment is None:
            raise errors.PaymentNotFoundError(
                f"Payment not found: {payment_id}",
                payment_id=payment_id,
            )

        if payment.status != models.PaymentStatusType.PENDING:
            logger.info(
                "Payment already processed payment_id=%s status=%s",
                payment_id,
                payment.status,
            )
            return

        is_success = await gateway.emulate_payment_gateway(self._config)
        webhook_status = (
            schemas.PaymentWebhookStatus.SUCCEEDED if is_success else schemas.PaymentWebhookStatus.FAILED
        )

        await self._deliver_webhook(
            payment_id=payment_id,
            webhook_url=payment.webhook_url,
            status=webhook_status,
        )

        if is_success:
            await self._payments_repository.mark_succeeded(payment_id=payment_id)
        else:
            await self._payments_repository.mark_failed(
                payment_id=payment_id,
                error_message="Gateway processing simulation failed",
            )

    @async_retry(
        attempts=3,
        exceptions=(httpx.HTTPError,),
        reraise=True,
        log_final_error=False,
    )
    async def _deliver_webhook(
        self,
        *,
        payment_id: uuid.UUID,
        webhook_url: str,
        status: schemas.PaymentWebhookStatus,
    ) -> None:
        response = await self._http_client.post(
            webhook_url,
            json=schemas.PaymentWebhookPayload(
                payment_id=payment_id,
                status=status,
            ).model_dump(mode="json"),
        )
        response.raise_for_status()
