# Execution Timing

Wraps every function to measure and report execution time. Uses separate wrappers for sync and async functions.

## Code

```python title="examples/basic_timing.py"
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


def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def quick_function() -> str:
    return "done"


if __name__ == "__main__":
    wrap_all((time_sync, time_async))

    quick_function()
    fibonacci(10)
```

## Run it

```bash
python examples/basic_timing.py
```

## Expected output

```
⏱  quick_function took 0.00ms
⏱  fibonacci took 0.00ms
⏱  fibonacci took 0.00ms
⏱  fibonacci took 0.01ms
...
⏱  fibonacci took 0.03ms
```

## Key takeaway

Pass a `(sync_wrapper, async_wrapper)` tuple to `wrap_all()` to handle both sync and async functions. Each wrapper gets the same [wrapt signature](https://wrapt.readthedocs.io/en/latest/wrappers.html) — the async version just `await`s the call.
