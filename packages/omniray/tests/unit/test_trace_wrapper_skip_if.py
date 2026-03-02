"""Unit tests for create_trace_wrapper() — skip_if predicate logic."""

import pytest
from omniray.decorators import create_trace_wrapper
from omniray.tracing.tracers import AsyncTracer, Tracer

# ── skip_if on functions ──────────────────────────────────────────────


def test_sync_skip_if_true(mocker):
    """Sync: skip_if=True bypasses Tracer.trace entirely."""
    mock_trace = mocker.patch.object(Tracer, "trace")

    sync_wrapper, _ = create_trace_wrapper(skip_if=lambda x: x == "skip")

    def wrapped_func(x):
        return f"result_{x}"

    result = sync_wrapper(wrapped_func, None, ("skip",), {})

    assert result == "result_skip"
    mock_trace.assert_not_called()


def test_sync_skip_if_false(mocker):
    """Sync: skip_if=False proceeds with tracing."""
    mocker.patch.object(Tracer, "trace", return_value="traced_result")

    sync_wrapper, _ = create_trace_wrapper(skip_if=lambda x: x == "skip")

    def wrapped_func(x):
        return f"result_{x}"

    result = sync_wrapper(wrapped_func, None, ("do_trace",), {})

    assert result == "traced_result"
    Tracer.trace.assert_called_once()


@pytest.mark.asyncio
async def test_async_skip_if_true(mocker):
    """Async: skip_if=True bypasses AsyncTracer.trace entirely."""
    mock_trace = mocker.patch.object(AsyncTracer, "trace")

    _, async_wrapper = create_trace_wrapper(skip_if=lambda x: x == "skip")

    async def wrapped_func(x):
        return f"result_{x}"

    result = await async_wrapper(wrapped_func, None, ("skip",), {})

    assert result == "result_skip"
    mock_trace.assert_not_called()


@pytest.mark.asyncio
async def test_async_skip_if_false(mocker):
    """Async: skip_if=False proceeds with tracing."""

    async def mock_trace_fn(*_args, **_kwargs):
        return "async_traced_result"

    mocker.patch.object(AsyncTracer, "trace", side_effect=mock_trace_fn)

    _, async_wrapper = create_trace_wrapper(skip_if=lambda x: x == "skip")

    async def wrapped_func(x):
        return f"result_{x}"

    result = await async_wrapper(wrapped_func, None, ("do_trace",), {})

    assert result == "async_traced_result"
    AsyncTracer.trace.assert_called_once()


# ── skip_if on methods (wrapt strips self) ────────────────────────────


def test_skip_if_on_method_no_self_in_args(mocker):
    """skip_if receives args WITHOUT self — wrapt strips it to instance param."""
    mock_trace = mocker.patch.object(Tracer, "trace")
    predicate = mocker.Mock(return_value=True)

    sync_wrapper, _ = create_trace_wrapper(skip_if=predicate)

    def method(x):
        return f"result_{x}"

    # wrapt signature: (wrapped, instance, args, kwargs)
    result = sync_wrapper(method, object(), ("val",), {})

    assert result == "result_val"
    predicate.assert_called_once_with("val")
    mock_trace.assert_not_called()
