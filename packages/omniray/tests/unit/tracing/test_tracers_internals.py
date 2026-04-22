"""Unit tests for Tracer private methods."""

import pytest
from omniray.tracing.flags import TraceFlags
from omniray.tracing.tracers import AsyncTracer, Tracer

# ── _init_tracing ─────────────────────────────────────────────────────


def test_init_tracing(mocker):
    """Test _init_tracing sets span attributes."""
    mock_span = mocker.MagicMock()

    start_time = Tracer._init_tracing(mock_span, current_depth=2)

    mock_span.set_attribute.assert_called_once_with("depth", 2)
    assert isinstance(start_time, float)


# ── _setup_trace ──────────────────────────────────────────────────────


def _setup_trace_helper():
    return None


def test_setup_trace_logging_disabled():
    """Test _setup_trace returns span name but zero depth when log=False."""
    flags = TraceFlags(
        log=False,
        log_input=True,
        log_output=False,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    span_name, depth, _, _ = Tracer._setup_trace(_setup_trace_helper, (), {}, flags)

    # Span name is always generated for Azure Application Insights
    assert span_name == "_setup_trace_helper"
    assert depth == 0


def test_setup_trace_logging_enabled(mocker):
    """Test _setup_trace returns proper values when log=True."""
    mocker.patch("omniray.tracing.tracers.logger")
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")
    mock_call_depth = mocker.patch("omniray.tracing.tracers._call_depth")
    mock_call_depth.get.return_value = 0
    flags = TraceFlags(
        log=True,
        log_input=True,
        log_output=False,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    span_name, depth, _, _ = Tracer._setup_trace(_setup_trace_helper, (), {}, flags)

    assert span_name == "_setup_trace_helper"
    assert depth == 0
    mock_io_logger.log_input.assert_called_once()


def test_setup_trace_no_input_logging(mocker):
    """Test _setup_trace skips input logging when disabled."""
    mocker.patch("omniray.tracing.tracers.logger")
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")
    mock_call_depth = mocker.patch("omniray.tracing.tracers._call_depth")
    mock_call_depth.get.return_value = 0
    flags = TraceFlags(
        log=True,
        log_input=False,
        log_output=False,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    def test_func():
        return None

    Tracer._setup_trace(test_func, (), {}, flags)

    mock_io_logger.log_input.assert_not_called()


# ── _finish_tracing ───────────────────────────────────────────────────


def test_finish_tracing_logging_disabled(mocker):
    """Test _finish_tracing does nothing when log=False."""
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    flags = TraceFlags(
        log=False,
        log_input=True,
        log_output=True,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    Tracer._finish_tracing("result", "span_name", 0.1, 0, flags, None, None)

    mock_profiler.log_span_success.assert_not_called()


def test_finish_tracing_logging_enabled(mocker):
    """Test _finish_tracing logs when log=True."""
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")
    flags = TraceFlags(
        log=True,
        log_input=False,
        log_output=True,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    Tracer._finish_tracing("result", "span_name", 0.1, 0, flags, None, None)

    mock_profiler.log_span_success.assert_called_once_with(
        "span_name",
        100.0,
        0,
        input_size_mb=None,
        output_size_mb=None,
        rss_current_mb=None,
        rss_delta_mb=None,
        rss_peak_mb=None,
    )
    mock_io_logger.log_output.assert_called_once_with("result", 0)
    mock_profiler.log_section_separator.assert_called_once_with(0)


def test_finish_tracing_no_output_logging(mocker):
    """Test _finish_tracing skips output logging when disabled."""
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    mock_io_logger = mocker.patch.object(Tracer, "io_logger")
    flags = TraceFlags(
        log=True,
        log_input=False,
        log_output=False,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    Tracer._finish_tracing("result", "span_name", 0.1, 0, flags, None, None)

    mock_profiler.log_span_success.assert_called_once()
    mock_io_logger.log_output.assert_not_called()


# ── _finish_tracing_failure ───────────────────────────────────────────


def test_finish_tracing_failure_logging_enabled(mocker):
    """Test _finish_tracing_failure logs when log=True."""
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    mock_span = mocker.MagicMock()
    exception = ValueError("test")
    flags = TraceFlags(
        log=True,
        log_input=False,
        log_output=False,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    Tracer._finish_tracing_failure(mock_span, 0.05, "span_name", 1, exception, flags)

    mock_profiler.log_span_failure.assert_called_once_with("span_name", 50.0, 1)


def test_finish_tracing_failure_logging_disabled(mocker):
    """Test _finish_tracing_failure skips logging when log=False."""
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    mock_span = mocker.MagicMock()
    exception = ValueError("test")
    flags = TraceFlags(
        log=False,
        log_input=False,
        log_output=False,
        log_input_size=False,
        log_output_size=False,
        log_rss=False,
        otel=False,
    )

    Tracer._finish_tracing_failure(mock_span, 0.05, "span_name", 1, exception, flags)

    mock_profiler.log_span_failure.assert_not_called()
    mock_span.set_attribute.assert_not_called()  # otel=False → no span error recording


# ── _update_depth ─────────────────────────────────────────────────────


def test_update_depth(mocker):
    """Test _update_depth increments depth and logs."""
    mocker.patch("omniray.tracing.tracers.logger")
    mock_profiler = mocker.patch.object(Tracer, "profiler")
    # Mock _call_depth to avoid context isolation issues with pytest-asyncio
    mock_call_depth = mocker.patch("omniray.tracing.tracers._call_depth")
    initial_depth = 2
    mock_call_depth.get.return_value = initial_depth

    depth = Tracer._update_depth("test_span")

    assert depth == initial_depth
    mock_call_depth.set.assert_called_once_with(initial_depth + 1)
    mock_profiler.get_indent.assert_called_once()


# ── _trace_span_error / _trace_duration ───────────────────────────────


def test_trace_span_error(mocker):
    """Test _trace_span_error sets span error attributes."""
    mock_span = mocker.MagicMock()
    exception = ValueError("test error message")

    Tracer._trace_span_error(mock_span, exception)

    mock_span.set_attribute.assert_any_call("error.type", "ValueError")
    mock_span.set_attribute.assert_any_call("error.message", "test error message")
    mock_span.record_exception.assert_called_once_with(exception)
    mock_span.set_status.assert_called_once()


def test_trace_duration(mocker):
    """Test _trace_duration sets duration attribute."""
    mock_span = mocker.MagicMock()

    Tracer._trace_duration(mock_span, 1.5)

    mock_span.set_attribute.assert_called_once_with("duration_seconds", 1.5)


# ── defensive hardening: tracing crash must not mask user exceptions ──


def _raise_value_error():
    msg = "user error"
    raise ValueError(msg)


async def _async_raise_value_error():
    msg = "user error"
    raise ValueError(msg)


def test_finish_tracing_failure_crash_preserves_user_exception(mocker):
    """Crash in _finish_tracing_failure must not replace the user exception."""
    mocker.patch.object(Tracer, "_trace_span_error", side_effect=RuntimeError("span ended"))
    mocker.patch.object(Tracer, "_trace_duration")
    mocker.patch("omniray.tracing.tracers._call_depth")

    with pytest.raises(ValueError, match="user error"):
        Tracer.trace(_raise_value_error, (), {}, otel=True)


def test_trace_duration_crash_preserves_user_exception(mocker):
    """Crash in _trace_duration (finally) must not replace the user exception."""
    mocker.patch.object(Tracer, "_trace_duration", side_effect=RuntimeError("otel crash"))
    mocker.patch("omniray.tracing.tracers._call_depth")

    with pytest.raises(ValueError, match="user error"):
        Tracer.trace(_raise_value_error, (), {})


@pytest.mark.asyncio
async def test_async_finish_tracing_failure_crash_preserves_user_exception(mocker):
    """Async: crash in _finish_tracing_failure must not replace the user exception."""
    mocker.patch.object(AsyncTracer, "_trace_span_error", side_effect=RuntimeError("span ended"))
    mocker.patch.object(AsyncTracer, "_trace_duration")
    mocker.patch("omniray.tracing.tracers._call_depth")

    with pytest.raises(ValueError, match="user error"):
        await AsyncTracer.trace(_async_raise_value_error, (), {}, otel=True)


@pytest.mark.asyncio
async def test_async_trace_duration_crash_preserves_user_exception(mocker):
    """Async: crash in _trace_duration (finally) must not replace the user exception."""
    mocker.patch.object(AsyncTracer, "_trace_duration", side_effect=RuntimeError("otel crash"))
    mocker.patch("omniray.tracing.tracers._call_depth")

    with pytest.raises(ValueError, match="user error"):
        await AsyncTracer.trace(_async_raise_value_error, (), {})
