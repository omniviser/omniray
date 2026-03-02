"""Unit tests for Tracer.trace() / AsyncTracer.trace() — core execution paths."""

import asyncio

import pytest
from omniray.tracing.tracers import (
    AsyncTracer,
    Tracer,
)

# ── Sync success / failure ────────────────────────────────────────────


def test_trace_sync_success(mocker):
    """Test synchronous trace execution success path."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_FLAG", new=None)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, log_output=True)

    assert result == "result"
    mock_profiler.log_span_success.assert_called_once()
    mock_io_logger.log_output.assert_called_once()


def test_trace_sync_failure(mocker):
    """Test synchronous trace execution failure path."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_profiler = mocker.patch.object(Tracer, "profiler")

    error_msg = "test error"

    def failing_func():
        raise ValueError(error_msg)

    with pytest.raises(ValueError, match="test error"):
        Tracer.trace(failing_func, (), {})

    mock_profiler.log_span_failure.assert_called_once()


# ── Async success / failure ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_trace_async_success(mocker):
    """Test asynchronous trace execution success path."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_FLAG", new=None)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_profiler = mocker.patch.object(AsyncTracer, "profiler")
    mock_io_logger = mocker.patch.object(AsyncTracer, "io_logger")

    async def async_func():
        await asyncio.sleep(0)
        return "async_result"

    result = await AsyncTracer.trace(async_func, (), {}, log_output=True)

    assert result == "async_result"
    mock_profiler.log_span_success.assert_called_once()
    mock_io_logger.log_output.assert_called_once()


@pytest.mark.asyncio
async def test_trace_async_failure(mocker):
    """Test asynchronous trace execution failure path."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_profiler = mocker.patch.object(AsyncTracer, "profiler")

    error_msg = "async error"

    async def failing_async_func():
        await asyncio.sleep(0)
        raise RuntimeError(error_msg)

    with pytest.raises(RuntimeError, match="async error"):
        await AsyncTracer.trace(failing_async_func, (), {})

    mock_profiler.log_span_failure.assert_called_once()


# ── BaseException handling ────────────────────────────────────────────


def test_trace_sync_handles_base_exception(mocker):
    """Test that trace handles BaseException without UnboundLocalError.

    BaseException (like KeyboardInterrupt) is not caught by 'except Exception', so duration_s would
    be unset when finally block runs if not initialized.
    """
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")

    def failing_func():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        Tracer.trace(failing_func, (), {})


@pytest.mark.asyncio
async def test_trace_async_handles_base_exception(mocker):
    """Test that async trace handles BaseException without UnboundLocalError.

    BaseException (like KeyboardInterrupt) is not caught by 'except Exception', so duration_s would
    be unset when finally block runs if not initialized.
    """
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")

    async def failing_async_func():
        await asyncio.sleep(0)
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        await AsyncTracer.trace(failing_async_func, (), {})
