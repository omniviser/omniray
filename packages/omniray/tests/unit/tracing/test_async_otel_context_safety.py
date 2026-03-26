"""Regression test for OTel context detach error in AsyncTracer.trace().

Production error:
    ERROR:opentelemetry.context: Failed to detach context
    ValueError: <Token> was created in a different Context

start_as_current_span() uses a generator-based context manager whose token
is bound to the current contextvars.Context. In async code with create_task(),
GC can finalise the generator in a different context copy, causing the error.

Fix: AsyncTracer uses start_span() + manual attach/detach (no generator).
"""

import asyncio

from omniray.tracing.tracers import AsyncTracer


def test_async_tracer_uses_start_span_not_start_as_current_span(mocker):
    """AsyncTracer.trace() must use start_span(), not start_as_current_span()."""
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.HAS_OTEL", new=True)

    async def func():
        return "ok"

    result = asyncio.run(AsyncTracer.trace(func, (), {}, otel=True))

    assert result == "ok"
    mock_tracer.start_span.assert_called_once()
    mock_tracer.start_as_current_span.assert_not_called()
