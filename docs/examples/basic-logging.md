# Basic Logging

Wraps every function to log calls with arguments and return values. No manual decorators needed — one line at startup instruments your entire codebase.

## Code

```python title="examples/basic_logging.py"
import logging

from omniwrap import wrap_all

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def log_calls(wrapped, instance, args, kwargs):
    """Log every function call with its arguments and return value."""
    name = wrapped.__qualname__
    logger.info("→ %s(args=%s, kwargs=%s)", name, args, kwargs)
    result = wrapped(*args, **kwargs)
    logger.info("← %s returned %s", name, result)
    return result


def add(a: int, b: int) -> int:
    return a + b


def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    wrap_all(log_calls)

    add(2, 3)
    greet("World")
```

## Run it

```bash
python examples/basic_logging.py
```

## Expected output

```
→ add(args=(2, 3), kwargs={})
← add returned 5
→ greet(args=('World',), kwargs={})
← greet returned Hello, World!
```

## Key takeaway

A single `wrap_all(log_calls)` call instruments every function in your codebase. The wrapper receives the original function, instance (for methods), args, and kwargs — the standard [wrapt signature](https://wrapt.readthedocs.io/en/latest/wrappers.html).
