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
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")
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
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")

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
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")
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
    mock_profiler = mocker.patch("omniray.tracing.tracers.profilers")

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


# ── Size tracking (sync) ──────────────────────────────────────────────


def _setup_size_mocks(mocker, *, input_size_flag, output_size_flag):
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_SIZE_FLAG", new=input_size_flag)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_SIZE_FLAG", new=output_size_flag)
    mocker.patch("omniray.tracing.flags._default_flags_cache", new={})
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mocker.patch("omniray.tracing.tracers.logger")
    return mocker.patch("omniray.tracing.tracers.profilers")


def test_trace_sync_size_flags_off_passes_none(mocker):
    """Both size flags off → log_span_success called with both kwargs=None."""
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=False, output_size_flag=False)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb")

    def sample_func():
        return "ok"

    Tracer.trace(sample_func, (), {})

    mock_measure.assert_not_called()
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] is None
    assert kwargs["output_size_mb"] is None


def test_trace_sync_input_size_flag_on_passes_to_profiler(mocker):
    """input_size flag on → log_span_success receives input_size_mb from measure_size_mb."""
    input_mb = 0.1
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=True, output_size_flag=False)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[input_mb])

    def sample_func(_x):
        return "ok"

    Tracer.trace(sample_func, ("arg",), {})

    mock_measure.assert_called_once_with((("arg",), {}))
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == input_mb
    assert kwargs["output_size_mb"] is None


def test_trace_sync_output_size_flag_on_passes_to_profiler(mocker):
    """output_size flag on → log_span_success receives output_size_mb from measure_size_mb."""
    output_mb = 2.5
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=False, output_size_flag=True)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[output_mb])

    def sample_func():
        return "result"

    Tracer.trace(sample_func, (), {})

    mock_measure.assert_called_once_with("result")
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["output_size_mb"] == output_mb
    assert kwargs["input_size_mb"] is None


def test_trace_sync_both_size_flags_on_passes_both(mocker):
    """Both size flags on → both kwargs populated; input measured before output."""
    input_mb, output_mb = 0.1, 2.5
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=True, output_size_flag=True)
    mock_measure = mocker.patch(
        "omniray.tracing.tracers.measure_size_mb", side_effect=[input_mb, output_mb]
    )

    def sample_func(_x):
        return "result"

    Tracer.trace(sample_func, ("arg",), {})

    assert mock_measure.call_args_list[0].args == ((("arg",), {}),)
    assert mock_measure.call_args_list[1].args == ("result",)
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == input_mb
    assert kwargs["output_size_mb"] == output_mb


def test_trace_sync_output_size_on_exception_not_measured(mocker):
    """Function raises → log_span_success not called, measure_size_mb not called for result."""
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=False, output_size_flag=True)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb")

    def failing_func():
        msg = "boom"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="boom"):
        Tracer.trace(failing_func, (), {})

    mock_measure.assert_not_called()
    mock_profiler.log_span_success.assert_not_called()
    mock_profiler.log_span_failure.assert_called_once()


# ── Size tracking (async) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trace_async_input_size_flag_on_passes_to_profiler(mocker):
    input_mb = 0.1
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=True, output_size_flag=False)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[input_mb])

    async def async_func(_x):
        await asyncio.sleep(0)
        return "ok"

    await AsyncTracer.trace(async_func, ("arg",), {})

    mock_measure.assert_called_once_with((("arg",), {}))
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == input_mb
    assert kwargs["output_size_mb"] is None


@pytest.mark.asyncio
async def test_trace_async_output_size_flag_on_passes_to_profiler(mocker):
    output_mb = 2.5
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=False, output_size_flag=True)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[output_mb])

    async def async_func():
        await asyncio.sleep(0)
        return "result"

    await AsyncTracer.trace(async_func, (), {})

    mock_measure.assert_called_once_with("result")
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["output_size_mb"] == output_mb


@pytest.mark.asyncio
async def test_trace_async_both_size_flags_on_passes_both(mocker):
    input_mb, output_mb = 0.1, 2.5
    expected_measure_calls = 2
    mock_profiler = _setup_size_mocks(mocker, input_size_flag=True, output_size_flag=True)
    mock_measure = mocker.patch(
        "omniray.tracing.tracers.measure_size_mb", side_effect=[input_mb, output_mb]
    )

    async def async_func(_x):
        await asyncio.sleep(0)
        return "result"

    await AsyncTracer.trace(async_func, ("arg",), {})

    assert mock_measure.call_count == expected_measure_calls
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == input_mb
    assert kwargs["output_size_mb"] == output_mb


# ── RSS tracking ──────────────────────────────────────────────────────


def _setup_rss_mocks(mocker, *, rss_flag):
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_RSS_FLAG", new=rss_flag)
    mocker.patch("omniray.tracing.flags._default_flags_cache", new={})
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mocker.patch("omniray.tracing.tracers.logger")
    return mocker.patch("omniray.tracing.tracers.profilers")


def test_trace_sync_rss_flag_off_skips_measurement(mocker):
    """log_rss off → rss readers not called; rss kwargs None on profiler call."""
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=False)
    mock_read = mocker.patch("omniray.tracing.tracers.read_rss_mb")
    mock_peak = mocker.patch("omniray.tracing.tracers.read_peak_rss_mb")

    def sample_func():
        return "ok"

    Tracer.trace(sample_func, (), {})

    mock_read.assert_not_called()
    mock_peak.assert_not_called()
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["rss_current_mb"] is None
    assert kwargs["rss_delta_mb"] is None
    assert kwargs["rss_peak_mb"] is None


def test_trace_sync_rss_flag_on_passes_peak(mocker):
    """log_rss on → read_peak_rss_mb called after wrapped; value reaches profiler."""
    peak_mb = 3000.5
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=True)
    mocker.patch("omniray.tracing.tracers.read_rss_mb", side_effect=[10.0, 12.0])
    mock_peak = mocker.patch("omniray.tracing.tracers.read_peak_rss_mb", return_value=peak_mb)

    def sample_func():
        return "ok"

    Tracer.trace(sample_func, (), {})

    mock_peak.assert_called_once()
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["rss_peak_mb"] == peak_mb


def test_trace_sync_rss_peak_raised_to_current_when_kernel_lags(mocker):
    """Linux kernel can report ru_maxrss < current RSS briefly — enforce peak >= current."""
    current_mb = 196.42
    reported_peak_mb = 195.88  # below current — kernel lag
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=True)
    mocker.patch("omniray.tracing.tracers.read_rss_mb", side_effect=[100.0, current_mb])
    mocker.patch("omniray.tracing.tracers.read_peak_rss_mb", return_value=reported_peak_mb)

    def sample_func():
        return "ok"

    Tracer.trace(sample_func, (), {})

    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["rss_current_mb"] == current_mb
    assert kwargs["rss_peak_mb"] == current_mb  # raised to current


def test_trace_sync_rss_flag_on_passes_current_and_delta(mocker):
    """log_rss on → profiler receives rss_current_mb and computed delta."""
    before_mb, after_mb = 100.0, 112.34
    expected_read_calls = 2
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=True)
    mock_read = mocker.patch(
        "omniray.tracing.tracers.read_rss_mb", side_effect=[before_mb, after_mb]
    )

    def sample_func():
        return "ok"

    Tracer.trace(sample_func, (), {})

    assert mock_read.call_count == expected_read_calls
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["rss_current_mb"] == after_mb
    assert kwargs["rss_delta_mb"] == pytest.approx(after_mb - before_mb, abs=1e-9)


def test_trace_sync_rss_flag_on_exception_skips_after(mocker):
    """Exception → read_rss_mb called only for before; log_span_success not called."""
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=True)
    mock_read = mocker.patch("omniray.tracing.tracers.read_rss_mb", side_effect=[100.0])

    def failing_func():
        msg = "boom"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="boom"):
        Tracer.trace(failing_func, (), {})

    assert mock_read.call_count == 1
    mock_profiler.log_span_success.assert_not_called()


@pytest.mark.asyncio
async def test_trace_async_rss_flag_on_passes_current_and_delta(mocker):
    """Async mirror: rss on → current + delta reach profiler."""
    before_mb, after_mb = 50.0, 75.5
    expected_read_calls = 2
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=True)
    mock_read = mocker.patch(
        "omniray.tracing.tracers.read_rss_mb", side_effect=[before_mb, after_mb]
    )

    async def async_func():
        await asyncio.sleep(0)
        return "ok"

    await AsyncTracer.trace(async_func, (), {})

    assert mock_read.call_count == expected_read_calls
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["rss_current_mb"] == after_mb
    assert kwargs["rss_delta_mb"] == pytest.approx(after_mb - before_mb, abs=1e-9)


def test_trace_sync_rss_read_fails_gracefully(mocker):
    """read_rss_mb returning None → profiler gets both rss kwargs as None."""
    mock_profiler = _setup_rss_mocks(mocker, rss_flag=True)
    mocker.patch("omniray.tracing.tracers.read_rss_mb", return_value=None)

    def sample_func():
        return "ok"

    Tracer.trace(sample_func, (), {})

    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["rss_current_mb"] is None
    assert kwargs["rss_delta_mb"] is None
