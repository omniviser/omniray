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


# ── Size tracking (sync) ──────────────────────────────────────────────


def _setup_size_mocks(mocker, tracer_cls, *, input_size_flag, output_size_flag):
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_SIZE_FLAG", new=input_size_flag)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_SIZE_FLAG", new=output_size_flag)
    mocker.patch("omniray.tracing.flags._default_flags_cache", new={})
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mocker.patch("omniray.tracing.tracers.logger")
    return mocker.patch.object(tracer_cls, "profiler")


def test_trace_sync_size_flags_off_passes_none(mocker):
    """Both size flags off → log_span_success called with both kwargs=None."""
    mock_profiler = _setup_size_mocks(mocker, Tracer, input_size_flag=False, output_size_flag=False)
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
    mock_profiler = _setup_size_mocks(mocker, Tracer, input_size_flag=True, output_size_flag=False)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[0.1])

    def sample_func(_x):
        return "ok"

    Tracer.trace(sample_func, ("arg",), {})

    mock_measure.assert_called_once_with((("arg",), {}))
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == 0.1
    assert kwargs["output_size_mb"] is None


def test_trace_sync_output_size_flag_on_passes_to_profiler(mocker):
    """output_size flag on → log_span_success receives output_size_mb from measure_size_mb."""
    mock_profiler = _setup_size_mocks(mocker, Tracer, input_size_flag=False, output_size_flag=True)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[2.5])

    def sample_func():
        return "result"

    Tracer.trace(sample_func, (), {})

    mock_measure.assert_called_once_with("result")
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["output_size_mb"] == 2.5
    assert kwargs["input_size_mb"] is None


def test_trace_sync_both_size_flags_on_passes_both(mocker):
    """Both size flags on → both kwargs populated; input measured before output."""
    mock_profiler = _setup_size_mocks(mocker, Tracer, input_size_flag=True, output_size_flag=True)
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[0.1, 2.5])

    def sample_func(_x):
        return "result"

    Tracer.trace(sample_func, ("arg",), {})

    assert mock_measure.call_args_list[0].args == ((("arg",), {}),)
    assert mock_measure.call_args_list[1].args == ("result",)
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == 0.1
    assert kwargs["output_size_mb"] == 2.5


def test_trace_sync_output_size_on_exception_not_measured(mocker):
    """Function raises → log_span_success not called, measure_size_mb not called for result."""
    mock_profiler = _setup_size_mocks(mocker, Tracer, input_size_flag=False, output_size_flag=True)
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
    mock_profiler = _setup_size_mocks(
        mocker, AsyncTracer, input_size_flag=True, output_size_flag=False
    )
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[0.1])

    async def async_func(_x):
        await asyncio.sleep(0)
        return "ok"

    await AsyncTracer.trace(async_func, ("arg",), {})

    mock_measure.assert_called_once_with((("arg",), {}))
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == 0.1
    assert kwargs["output_size_mb"] is None


@pytest.mark.asyncio
async def test_trace_async_output_size_flag_on_passes_to_profiler(mocker):
    mock_profiler = _setup_size_mocks(
        mocker, AsyncTracer, input_size_flag=False, output_size_flag=True
    )
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[2.5])

    async def async_func():
        await asyncio.sleep(0)
        return "result"

    await AsyncTracer.trace(async_func, (), {})

    mock_measure.assert_called_once_with("result")
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["output_size_mb"] == 2.5


@pytest.mark.asyncio
async def test_trace_async_both_size_flags_on_passes_both(mocker):
    mock_profiler = _setup_size_mocks(
        mocker, AsyncTracer, input_size_flag=True, output_size_flag=True
    )
    mock_measure = mocker.patch("omniray.tracing.tracers.measure_size_mb", side_effect=[0.1, 2.5])

    async def async_func(_x):
        await asyncio.sleep(0)
        return "result"

    await AsyncTracer.trace(async_func, ("arg",), {})

    assert mock_measure.call_count == 2
    kwargs = mock_profiler.log_span_success.call_args.kwargs
    assert kwargs["input_size_mb"] == 0.1
    assert kwargs["output_size_mb"] == 2.5
