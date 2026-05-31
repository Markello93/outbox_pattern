import uuid

import fastapi

from app.api import dependencies
from app.api.payment.v1 import schemas, service

router = fastapi.APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[fastapi.Depends(dependencies.verify_api_key)],
)


@router.post(
    "",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    response_model=schemas.PaymentCreateResponse,
    summary="Создание платежа",
)
async def create_payment(
    request: schemas.PaymentCreateRequest,
    idempotency_key: uuid.UUID = fastapi.Header(alias="Idempotency-Key"),
    payment_service: service.PaymentService = dependencies.inject(service.PaymentService),
) -> schemas.PaymentCreateResponse:
    payment = await payment_service.create_payment(
        idempotency_key=idempotency_key,
        request=request,
    )
    return schemas.PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=schemas.PaymentDetailResponse,
    summary="Получение информации о платеже",
)
async def get_payment(
    payment_id: uuid.UUID,
    payment_service: service.PaymentService = dependencies.inject(service.PaymentService),
) -> schemas.PaymentDetailResponse:
    payment = await payment_service.get_payment(payment_id=payment_id)
    if payment is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return schemas.PaymentDetailResponse.model_validate(payment)
