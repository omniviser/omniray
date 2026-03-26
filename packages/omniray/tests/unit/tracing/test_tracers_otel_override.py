"""Tests for per-call otel override with tri-state semantics."""

import pytest
from omniray.tracing.tracers import (
    AsyncTracer,
    Tracer,
)


def test_trace_sync_otel_true_blocked_by_global_false(mocker):
    """_OTEL_FLAG=False is a kill switch — otel=True is ignored."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, otel=True)

    assert result == "result"
    mock_tracer.start_as_current_span.assert_not_called()


def test_trace_sync_otel_true_when_global_none(mocker):
    """_OTEL_FLAG=None lets otel=True create spans (local decides)."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=None)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, otel=True)

    assert result == "result"
    mock_tracer.start_as_current_span.assert_called_once()


def test_trace_sync_otel_false_overrides_global_true(mocker):
    """Otel=False suppresses span even when _OTEL_FLAG=True."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, otel=False)

    assert result == "result"
    mock_tracer.start_as_current_span.assert_not_called()


def test_trace_sync_otel_none_follows_global_true(mocker):
    """Otel=None defers to _OTEL_FLAG (True -> span created)."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {}, otel=None)

    assert result == "result"
    mock_tracer.start_as_current_span.assert_called_once()


def test_trace_sync_otel_none_follows_global_none(mocker):
    """Otel=None + _OTEL_FLAG=None -> no span (both unset, default off)."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=None)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    def sample_func():
        return "result"

    result = Tracer.trace(sample_func, (), {})

    assert result == "result"
    mock_tracer.start_as_current_span.assert_not_called()


@pytest.mark.asyncio
async def test_trace_async_otel_true_blocked_by_global_false(mocker):
    """Async: _OTEL_FLAG=False is a kill switch — otel=True is ignored."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    async def async_func():
        return "result"

    result = await AsyncTracer.trace(async_func, (), {}, otel=True)

    assert result == "result"
    mock_tracer.start_as_current_span.assert_not_called()


@pytest.mark.asyncio
async def test_trace_async_otel_true_when_global_none(mocker):
    """Async: _OTEL_FLAG=None lets otel=True create spans."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=None)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    async def async_func():
        return "result"

    result = await AsyncTracer.trace(async_func, (), {}, otel=True)

    assert result == "result"
    mock_tracer.start_span.assert_called_once()


@pytest.mark.asyncio
async def test_trace_async_otel_false_overrides_global_true(mocker):
    """Async: otel=False suppresses span even when _OTEL_FLAG=True."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    async def async_func():
        return "result"

    result = await AsyncTracer.trace(async_func, (), {}, otel=False)

    assert result == "result"
    mock_tracer.start_span.assert_not_called()


@pytest.mark.asyncio
async def test_trace_async_otel_none_follows_global_true(mocker):
    """Async: otel=None defers to _OTEL_FLAG (True -> span created)."""
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=True)
    mock_tracer = mocker.patch("omniray.tracing.tracers.otel_tracer")

    async def async_func():
        return "result"

    result = await AsyncTracer.trace(async_func, (), {}, otel=None)

    assert result == "result"
    mock_tracer.start_span.assert_called_once()
