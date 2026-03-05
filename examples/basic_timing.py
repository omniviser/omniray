"""Example: Automatic execution time measurement with omniwrap.

Wraps every function to measure and report execution time.
Useful for finding performance bottlenecks without manual profiling.

Usage:
    python examples/basic_timing.py
"""

import logging
import time

from omniwrap import wrap_all

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def time_sync(wrapped, instance, args, kwargs):
    """Measure execution time of synchronous functions."""
    start = time.perf_counter()
    result = wrapped(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("⏱  %s took %.2fms", wrapped.__qualname__, elapsed_ms)
    return result


async def time_async(wrapped, instance, args, kwargs):
    """Measure execution time of async functions."""
    start = time.perf_counter()
    result = await wrapped(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("⏱  %s took %.2fms", wrapped.__qualname__, elapsed_ms)
    return result


# --- Application code ---


def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def quick_function() -> str:
    return "done"


# --- Startup ---

if __name__ == "__main__":
    # Use separate wrappers for sync and async
    wrap_all((time_sync, time_async))

    quick_function()
    fibonacci(10)
