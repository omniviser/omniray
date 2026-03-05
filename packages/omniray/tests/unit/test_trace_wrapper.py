"""Unit tests for create_trace_wrapper() — basic dispatch and parameter forwarding."""

import pytest
from omniray.decorators import create_trace_wrapper
from omniray.tracing.tracers import AsyncTracer, Tracer

# ── Basic API ─────────────────────────────────────────────────────────


def test_returns_callable_tuple():
    """Returns tuple of (sync_wrapper, async_wrapper)."""
    sync_wrapper, async_wrapper = create_trace_wrapper()

    assert callable(sync_wrapper)
    assert callable(async_wrapper)


# ── Sync wrapper ──────────────────────────────────────────────────────


def test_sync_success(mocker):
    """Sync wrapper delegates to Tracer.trace and returns result."""
    mocker.patch.object(Tracer, "trace", return_value="traced_result")

    sync_wrapper, _ = create_trace_wrapper()

    def wrapped_func():
        return "success"

    result = sync_wrapper(wrapped_func, None, (), {})

    assert result == "traced_result"
    Tracer.trace.assert_called_once()


def test_sync_failure(mocker):
    """Sync wrapper propagates exception from Tracer.trace."""
    error_msg = "test error"
    mocker.patch.object(Tracer, "trace", side_effect=ValueError(error_msg))

    sync_wrapper, _ = create_trace_wrapper()

    def failing_func():
        raise ValueError(error_msg)

    with pytest.raises(ValueError, match="test error"):
        sync_wrapper(failing_func, None, (), {})


# ── Async wrapper ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_success(mocker):
    """Async wrapper delegates to AsyncTracer.trace and returns result."""

    async def mock_trace(*_args, **_kwargs):
        return "async_traced_result"

    mocker.patch.object(AsyncTracer, "trace", side_effect=mock_trace)

    _, async_wrapper = create_trace_wrapper()

    async def wrapped_func():
        return "async_success"

    result = await async_wrapper(wrapped_func, None, (), {})

    assert result == "async_traced_result"
    AsyncTracer.trace.assert_called_once()


@pytest.mark.asyncio
async def test_async_failure(mocker):
    """Async wrapper propagates exception from AsyncTracer.trace."""
    error_msg = "async error"

    async def mock_trace(*_args, **_kwargs):
        raise RuntimeError(error_msg)

    mocker.patch.object(AsyncTracer, "trace", side_effect=mock_trace)

    _, async_wrapper = create_trace_wrapper()

    async def failing_async_func():
        raise RuntimeError(error_msg)

    with pytest.raises(RuntimeError, match="async error"):
        await async_wrapper(failing_async_func, None, (), {})


# ── Parameter forwarding ──────────────────────────────────────────────


def test_params_forwarded_to_trace(mocker):
    """All params (log, log_input, log_output, otel) are forwarded to Tracer.trace."""
    mocker.patch.object(Tracer, "trace", return_value="result")

    sync_wrapper, _ = create_trace_wrapper(log=True, log_input=True, log_output=False, otel=True)

    def wrapped_func():
        return "success"

    sync_wrapper(wrapped_func, None, (), {})

    call_kwargs = Tracer.trace.call_args[1]
    assert call_kwargs["log"] is True
    assert call_kwargs["log_input"] is True
    assert call_kwargs["log_output"] is False
    assert call_kwargs["otel"] is True


def test_instance_forwarded_to_trace(mocker):
    """Wrapper forwards wrapt instance to Tracer.trace."""
    mocker.patch.object(Tracer, "trace", return_value="result")

    sync_wrapper, _ = create_trace_wrapper()

    class MyView:
        pass

    instance = MyView()

    def wrapped_func():
        return "success"

    sync_wrapper(wrapped_func, instance, (), {})

    call_kwargs = Tracer.trace.call_args[1]
    assert call_kwargs["instance"] is instance
