"""Unit tests for create_trace_wrapper() — flag resolution and OTel behavior."""

import pytest
from omniray.decorators import create_trace_wrapper
from omniray.tracing.tracers import Tracer

# ── OTel disabled ─────────────────────────────────────────────────────


def test_sync_without_otel(mocker):
    """Sync wrapper works when OTel is disabled — no span started."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    sync_wrapper, _ = create_trace_wrapper()

    def wrapped_func():
        return "success"

    result = sync_wrapper(wrapped_func, None, (), {})

    assert result == "success"
    mock_tracer.start_as_current_span.assert_not_called()


@pytest.mark.asyncio
async def test_async_without_otel(mocker):
    """Async wrapper works when OTel is disabled — no span started."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    _, async_wrapper = create_trace_wrapper()

    async def wrapped_func():
        return "async_success"

    result = await async_wrapper(wrapped_func, None, (), {})

    assert result == "async_success"
    mock_tracer.start_as_current_span.assert_not_called()


# ── Per-call resolution (not captured at factory time) ────────────────


def test_sync_per_call_resolution(mocker):
    """Flags are resolved per call, not captured at factory time."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_setup = mocker.patch.object(Tracer, "_setup_trace", return_value=("span_name", 0, None))
    mocker.patch.object(Tracer, "_init_tracing", return_value=0.0)
    mocker.patch.object(Tracer, "_finish_tracing")
    mocker.patch.object(Tracer, "_trace_duration")

    sync_wrapper, _ = create_trace_wrapper(log_input=True)

    def wrapped_func():
        return "success"

    # First call with _LOG_INPUT_FLAG=True — resolve_flag(True, True)=True, gated by log=True
    mocker.patch("omniray.tracing.flags.LOG_INPUT_FLAG", new=True)
    sync_wrapper(wrapped_func, None, (), {})
    flags1 = mock_setup.call_args[0][3]  # 4th positional arg is flags
    assert flags1.log_input is True

    # Reset and change flag to False (kill switch) — resolve_flag(False, True)=False
    mock_setup.reset_mock()
    mocker.patch("omniray.tracing.flags.LOG_INPUT_FLAG", new=False)
    sync_wrapper(wrapped_func, None, (), {})
    flags2 = mock_setup.call_args[0][3]
    assert flags2.log_input is False


def test_sync_otel_per_call(mocker):
    """Otel param is resolved per call in create_trace_wrapper."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=None)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")
    mocker.patch.object(Tracer, "_setup_trace", return_value=("span_name", 0, None))
    mocker.patch.object(Tracer, "_init_tracing", return_value=0.0)
    mocker.patch.object(Tracer, "_finish_tracing")
    mocker.patch.object(Tracer, "_trace_duration")

    sync_wrapper, _ = create_trace_wrapper(otel=True)

    def wrapped_func():
        return "success"

    sync_wrapper(wrapped_func, None, (), {})
    mock_tracer.start_as_current_span.assert_called_once()


def test_sync_log_param(mocker):
    """Log param controls console output in create_trace_wrapper."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=None)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_setup = mocker.patch.object(Tracer, "_setup_trace", return_value=("span_name", 0, None))
    mocker.patch.object(Tracer, "_init_tracing", return_value=0.0)
    mocker.patch.object(Tracer, "_finish_tracing")
    mocker.patch.object(Tracer, "_trace_duration")

    sync_wrapper, _ = create_trace_wrapper(log=True)

    def wrapped_func():
        return "success"

    sync_wrapper(wrapped_func, None, (), {})
    flags = mock_setup.call_args[0][3]
    assert flags.log is True


def test_sync_log_input_size_param_passes_through(mocker):
    """log_input_size forwarded through create_trace_wrapper into TraceFlags."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_setup = mocker.patch.object(Tracer, "_setup_trace", return_value=("span_name", 0, None))
    mocker.patch.object(Tracer, "_init_tracing", return_value=0.0)
    mocker.patch.object(Tracer, "_finish_tracing")
    mocker.patch.object(Tracer, "_trace_duration")

    sync_wrapper, _ = create_trace_wrapper(log_input_size=True)

    def wrapped_func():
        return "ok"

    sync_wrapper(wrapped_func, None, (), {})
    flags = mock_setup.call_args[0][3]
    assert flags.log_input_size is True


def test_sync_log_output_size_param_passes_through(mocker):
    """log_output_size forwarded through create_trace_wrapper into TraceFlags."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.tracers.otel_tracer")
    mock_setup = mocker.patch.object(Tracer, "_setup_trace", return_value=("span_name", 0, None))
    mocker.patch.object(Tracer, "_init_tracing", return_value=0.0)
    mocker.patch.object(Tracer, "_finish_tracing")
    mocker.patch.object(Tracer, "_trace_duration")

    sync_wrapper, _ = create_trace_wrapper(log_output_size=True)

    def wrapped_func():
        return "ok"

    sync_wrapper(wrapped_func, None, (), {})
    flags = mock_setup.call_args[0][3]
    assert flags.log_output_size is True
