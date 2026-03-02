"""Omniwrap - Automatically wrap every function in your codebase.

Apply any wrapt-compatible wrapper to all functions and methods across your entire application
with a single call at startup.

Example usage::

    from omniwrap import wrap_all

    # A simple logging wrapper (wrapt-compatible signature)
    def log_calls(wrapped, instance, args, kwargs):
        print(f"Calling {wrapped.__qualname__}")
        return wrapped(*args, **kwargs)

    # Single wrapper (applied to both sync and async)
    wrap_all(log_calls)

    # Separate sync/async wrappers
    wrap_all((sync_wrapper, async_wrapper))

    # Multiple wrappers (first = innermost)
    wrap_all(log_calls, (sync_trace, async_trace))

    # Disable explicitly
    wrap_all(log_calls, enabled=False)

    # Read from OMNIWRAP env var
    wrap_all(log_calls, enabled=None)
"""

import logging

from omniwrap.markers import skip_wrap
from omniwrap.wrapper import Wrapper

wrap_all = Wrapper.wrap_all
__all__ = ["skip_wrap", "wrap_all"]

logging.getLogger("omniwrap").addHandler(logging.NullHandler())
