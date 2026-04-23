"""Unit tests for flag resolution behavior inside Tracer.trace()."""

import asyncio

import pytest
from omniray.tracing.tracers import AsyncTracer, Tracer

# ── OTel disabled ─────────────────────────────────────────────────────


def test_trace_sync_without_otel_skips_span(mocker):
    """Test sync trace skips OTel span when OTEL_FLAG=False."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {})

    assert result == "result"
    mock_tracer.start_as_current_span.assert_not_called()


@pytest.mark.asyncio
async def test_trace_async_without_otel_skips_span(mocker):
    """Test async trace skips OTel span when OTEL_FLAG=False."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    async def async_func():
        await asyncio.sleep(0)
        return "async_result"

    result = await AsyncTracer.trace(async_func, (), {})

    assert result == "async_result"
    mock_tracer.start_as_current_span.assert_not_called()


def test_trace_sync_without_otel_console_still_works(mocker):
    """Test console profiling works when OTel is disabled."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.logger")
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {})

    assert result == "result"
    mock_profiler.log_span_success.assert_called_once()
    mock_io_logger.log_input.assert_called_once()
    mock_io_logger.log_output.assert_called_once()


def test_trace_sync_without_otel_error_no_real_span(mocker):
    """Test error path without OTel uses no-op span, not a real one."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.logger")
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    error_msg = "test error"

    def failing_func():
        raise ValueError(error_msg)

    with pytest.raises(ValueError, match="test error"):
        Tracer.trace(failing_func, (), {})

    mock_tracer.start_as_current_span.assert_not_called()
    mock_profiler.log_span_failure.assert_called_once()


# ── Tri-state resolution inside trace() ──────────────────────────────


def test_trace_log_true_overrides_global_none(mocker):
    """Per-function log=True activates console when global is unset."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=None)
    mocker.patch("omniray.tracing.tracers.logger")
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, log=True)

    assert result == "result"
    mock_profiler.log_span_success.assert_called_once()


def test_trace_log_true_blocked_by_global_false(mocker):
    """Per-function log=True is ignored when global is False (kill switch)."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=False)
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, log=True)

    assert result == "result"
    mock_profiler.log_span_success.assert_not_called()


def test_trace_log_false_overrides_global_true(mocker):
    """Per-function log=False disables console when global is True."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, log=False)

    assert result == "result"
    mock_profiler.log_span_success.assert_not_called()


def test_trace_log_input_gated_by_log(mocker):
    """log_input=True produces no output when log resolves to False."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=False)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_FLAG", new=True)
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")

    def sample_func():
        return "result"

    Tracer.trace(sample_func, (), {}, log_input=True)

    mock_io_logger.log_input.assert_not_called()
