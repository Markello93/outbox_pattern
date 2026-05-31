import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def async_retry(
    *,
    attempts: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    backoff_base: float = 2.0,
    reraise: bool = True,
    log_final_error: bool = True,
):

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < attempts:
                        delay = backoff_base ** (attempt - 1)
                        logger.warning(
                            "%s failed (attempt %s/%s), retry in %.1fs: %r",
                            func.__name__,
                            attempt,
                            attempts,
                            delay,
                            e,
                        )
                        await asyncio.sleep(delay)

            if log_final_error:
                logger.error("%s failed after %s attempts: %r", func.__name__, attempts, last_error)
            if reraise:
                raise last_error
            return None

        return wrapper

    return decorator
