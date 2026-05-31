import asyncio
import random

from app.core import settings


async def emulate_payment_gateway(config: settings.PaymentConsumerSettings) -> bool:
    """Имитация внешнего payment gateway"""
    processing_seconds = random.uniform(  # noqa: S311
        config.gateway_delay_min_seconds,
        config.gateway_delay_max_seconds,
    )
    await asyncio.sleep(processing_seconds)
    return random.random() < config.gateway_success_rate  # noqa: S311
