"""omniray - Function tracing and observability with console output and optional OpenTelemetry.

Provides automatic function/method tracing via OpenTelemetry spans.

Example usage::

    from omniwrap import wrap_all
    from omniray import create_trace_wrapper

    # Create sync and async wrappers
    wrappers = create_trace_wrapper()

    # Wrap everything with tracing
    wrap_all(wrappers)

    # With I/O logging enabled
    wrap_all(create_trace_wrapper(log_input=True, log_output=True))
"""

import logging

from omniray.decorators import create_trace_wrapper, trace

logging.getLogger("omniray").addHandler(logging.NullHandler())

__all__ = [
    "create_trace_wrapper",
    "trace",
]
