"""Unit tests for @trace(otel=...) parameter passthrough."""

import pytest
from omniray.decorators import trace
from omniray.tracing.tracers import AsyncTracer, Tracer


def test_otel_true_passed_to_sync_tracer(mocker):
    """@trace(otel=True) passes otel=True to Tracer.trace."""
    mocker.patch.object(Tracer, "trace", return_value="result")

    @trace(otel=True)
    def func():
        return "result"

    func()

    Tracer.trace.assert_called_once()
    assert Tracer.trace.call_args.kwargs["otel"] is True


@pytest.mark.asyncio
async def test_otel_false_passed_to_async_tracer(mocker):
    """@trace(otel=False) passes otel=False to AsyncTracer.trace."""

    async def mock_trace(*_args, **_kwargs):
        return "result"

    mocker.patch.object(AsyncTracer, "trace", side_effect=mock_trace)

    @trace(otel=False)
    async def func():
        return "result"

    await func()

    AsyncTracer.trace.assert_called_once()
    assert AsyncTracer.trace.call_args.kwargs["otel"] is False


def test_otel_default_none_passed(mocker):
    """@trace() passes otel=None to Tracer.trace."""
    mocker.patch.object(Tracer, "trace", return_value="result")

    @trace()
    def func():
        return "result"

    func()

    Tracer.trace.assert_called_once()
    assert Tracer.trace.call_args.kwargs["otel"] is None
