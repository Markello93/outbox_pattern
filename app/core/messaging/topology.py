from dataclasses import dataclass

from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue


@dataclass(frozen=True, slots=True)
class PaymentsTopology:
    exchange: str = "payments.exchange"
    routing_key: str = "payment.created"
    consumer_queue: str = "payments.processor.queue"
    retry_queue: str = "payments.processor.retry"
    dlx: str = "payments.dlx"
    dlq: str = "payments.processor.dlq"


payments = PaymentsTopology()


def business_exchange() -> RabbitExchange:
    return RabbitExchange(payments.exchange, type=ExchangeType.TOPIC, durable=True)


def dlx_exchange() -> RabbitExchange:
    return RabbitExchange(payments.dlx, type=ExchangeType.FANOUT, durable=True)


def main_queue(*, retry_routing_key: str = payments.retry_queue) -> RabbitQueue:
    return RabbitQueue(
        payments.consumer_queue,
        durable=True,
        routing_key=payments.routing_key,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": retry_routing_key,
        },
    )


def retry_queue(*, ttl_ms: int, main_routing_key: str = payments.consumer_queue) -> RabbitQueue:
    return RabbitQueue(
        payments.retry_queue,
        durable=True,
        arguments={
            "x-message-ttl": ttl_ms,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": main_routing_key,
        },
    )


def dlq_queue() -> RabbitQueue:
    return RabbitQueue(payments.dlq, durable=True)
