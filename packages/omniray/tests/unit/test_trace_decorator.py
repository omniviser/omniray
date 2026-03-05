"""Unit tests for @trace() decorator — basic dispatch and parameter forwarding."""

import pytest
from omniray.decorators import trace
from omniray.tracing.tracers import AsyncTracer, Tracer

# ── Sync / async dispatch ─────────────────────────────────────────────


def test_sync_function(mocker):
    """Sync function is traced via Tracer."""
    mocker.patch.object(Tracer, "trace", return_value="traced_result")

    @trace()
    def sync_func():
        return "result"

    result = sync_func()

    assert result == "traced_result"
    Tracer.trace.assert_called_once()


@pytest.mark.asyncio
async def test_async_function(mocker):
    """Async function is traced via AsyncTracer."""

    async def mock_trace(*_args, **_kwargs):
        return "async_traced_result"

    mocker.patch.object(AsyncTracer, "trace", side_effect=mock_trace)

    @trace()
    async def async_func():
        return "result"

    result = await async_func()

    assert result == "async_traced_result"
    AsyncTracer.trace.assert_called_once()


# ── Parameter forwarding ──────────────────────────────────────────────


def test_log_params_passed_as_none(mocker):
    """Default log/log_input/log_output=None are forwarded to Tracer.trace."""
    mocker.patch.object(Tracer, "trace", return_value="result")

    @trace()
    def func():
        return "result"

    func()

    call_kwargs = Tracer.trace.call_args[1]
    assert call_kwargs["log"] is None
    assert call_kwargs["log_input"] is None
    assert call_kwargs["log_output"] is None
    assert call_kwargs["otel"] is None


def test_log_params_passed_explicitly(mocker):
    """Explicit log/log_input/log_output values are forwarded to Tracer.trace."""
    mocker.patch.object(Tracer, "trace", return_value="result")

    @trace(log=True, log_input=True, log_output=False, otel=True)
    def func():
        return "result"

    func()

    call_kwargs = Tracer.trace.call_args[1]
    assert call_kwargs["log"] is True
    assert call_kwargs["log_input"] is True
    assert call_kwargs["log_output"] is False
    assert call_kwargs["otel"] is True
