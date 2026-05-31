import uuid


class PaymentDlqError(Exception):
    """Ошибка, при которой сообщение уходит в DLQ без retry."""

    def __init__(self, message: str, *, payment_id: uuid.UUID | None = None):
        super().__init__(message)
        self.payment_id = payment_id


class PaymentNotFoundError(PaymentDlqError):
    """payment_id из сообщения отсутствует в БД."""
