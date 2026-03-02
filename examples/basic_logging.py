"""Example: Automatic function call logging with omniwrap.

Wraps every function in your codebase to log calls with arguments and return values.
No manual decorators needed - just one line at startup.

Usage:
    python examples/basic_logging.py
"""

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


# --- Application code (would normally be in separate modules) ---


def add(a: int, b: int) -> int:
    return a + b


def greet(name: str) -> str:
    return f"Hello, {name}!"


# --- Startup ---

if __name__ == "__main__":
    # Wrap everything with logging - one line, entire codebase
    wrap_all(log_calls)

    # Now every call is automatically logged
    add(2, 3)
    greet("World")
