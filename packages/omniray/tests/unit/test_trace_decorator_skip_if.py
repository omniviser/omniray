"""Unit tests for @trace() decorator — skip_if predicate logic."""

import pytest
from omniray.decorators import trace
from omniray.tracing.tracers import AsyncTracer, Tracer

# ── skip_if on functions ──────────────────────────────────────────────


def test_skip_if_true_skips_tracing(mocker):
    """skip_if=True bypasses Tracer entirely."""
    mock_trace = mocker.patch.object(Tracer, "trace")

    @trace(skip_if=lambda x: x == "skip")
    def func(x):
        return f"result_{x}"

    result = func("skip")

    assert result == "result_skip"
    mock_trace.assert_not_called()


def test_skip_if_false_traces_normally(mocker):
    """skip_if=False proceeds with tracing."""
    mocker.patch.object(Tracer, "trace", return_value="traced_result")

    @trace(skip_if=lambda x: x == "skip")
    def func(x):
        return f"result_{x}"

    result = func("do_trace")

    assert result == "traced_result"
    Tracer.trace.assert_called_once()


@pytest.mark.asyncio
async def test_async_skip_if_true(mocker):
    """Async: skip_if=True bypasses AsyncTracer."""
    mock_trace = mocker.patch.object(AsyncTracer, "trace")

    @trace(skip_if=lambda x: x == "skip")
    async def func(x):
        return f"result_{x}"

    result = await func("skip")

    assert result == "result_skip"
    mock_trace.assert_not_called()


@pytest.mark.asyncio
async def test_async_skip_if_false(mocker):
    """Async: skip_if=False proceeds with tracing."""

    async def mock_trace_fn(*_args, **_kwargs):
        return "async_traced_result"

    mocker.patch.object(AsyncTracer, "trace", side_effect=mock_trace_fn)

    @trace(skip_if=lambda x: x == "skip")
    async def func(x):
        return f"result_{x}"

    result = await func("do_trace")

    assert result == "async_traced_result"
    AsyncTracer.trace.assert_called_once()


def test_skip_if_none_traces_normally(mocker):
    """Default skip_if=None proceeds with tracing."""
    mocker.patch.object(Tracer, "trace", return_value="traced_result")

    @trace()
    def func():
        return "result"

    result = func()

    assert result == "traced_result"
    Tracer.trace.assert_called_once()


def test_skip_if_receives_kwargs(mocker):
    """skip_if predicate receives keyword arguments."""
    mock_trace = mocker.patch.object(Tracer, "trace")
    predicate = mocker.Mock(return_value=True)

    @trace(skip_if=predicate)
    def func(*, key="default"):
        return f"result_{key}"

    result = func(key="skip")

    assert result == "result_skip"
    predicate.assert_called_once_with(key="skip")
    mock_trace.assert_not_called()


def test_skip_if_predicate_exception_propagates():
    """Exception in skip_if predicate propagates to caller (fail-fast)."""

    @trace(skip_if=lambda _x: 1 / 0)
    def func(x):
        return f"result_{x}"

    with pytest.raises(ZeroDivisionError):
        func("hello")


# ── skip_if on instance methods ───────────────────────────────────────


def test_skip_if_on_method_receives_self(mocker):
    """skip_if on @trace() method receives self as first arg."""
    mock_trace = mocker.patch.object(Tracer, "trace")
    predicate = mocker.Mock(return_value=True)

    class MyClass:
        @trace(skip_if=predicate)
        def method(self, x):
            return f"result_{x}"

    obj = MyClass()
    result = obj.method("val")

    assert result == "result_val"
    mock_trace.assert_not_called()
    # self is the first positional arg in @trace() context
    assert predicate.call_args[0][0] is obj
    assert predicate.call_args[0][1] == "val"
