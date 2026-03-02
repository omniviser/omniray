"""Tests for omniray behavior when OpenTelemetry is not installed."""

import sys
from contextlib import nullcontext

import pytest
from omniray.tracing.otel import _check_otel_env, _init_otel
from omniray.tracing.tracers import (
    AsyncTracer,
    Tracer,
)


def _patch_no_otel(mocker):
    """Simulate environment without OpenTelemetry installed."""
    mocker.patch("omniray.tracing.tracers.HAS_OTEL", new=False)
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=False)
    mocker.patch("omniray.tracing.tracers.otel_tracer", new=None)
    mocker.patch("omniray.tracing.tracers.NOOP_CONTEXT", new=nullcontext(None))


# --- _init_otel tests ---


def test_init_otel_returns_tracer_when_available():
    result = _init_otel(module_name="test")
    assert result.has_otel is True
    assert result.tracer is not None
    assert result.status is not None
    assert result.status_code is not None
    assert result.span_type is not None


def test_init_otel_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    result = _init_otel(module_name="test")
    assert result.has_otel is False
    assert result.tracer is None
    assert result.status is None
    assert result.span_type is None


# --- _check_otel_env tests ---


def test_check_otel_env_true_without_otel_raises():
    with pytest.raises(ImportError, match="pip install omniray"):
        _check_otel_env(flag=True, has_otel=False)


def test_check_otel_env_false_without_otel():
    assert _check_otel_env(flag=False, has_otel=False) is False


def test_check_otel_env_none_without_otel():
    """None (unset) is allowed even without OTel — per-function override may raise later."""
    assert _check_otel_env(flag=None, has_otel=False) is None


def test_check_otel_env_true_with_otel():
    assert _check_otel_env(flag=True, has_otel=True) is True


# --- Runtime behavior tests ---


def test_sync_trace_works_without_otel(mocker):
    """Console tracing works when OTel is not installed."""
    _patch_no_otel(mocker)
    expected = 3

    def add(a, b):
        return a + b

    result = Tracer.trace(add, (1, 2), {})
    assert result == expected


async def test_async_trace_works_without_otel(mocker):
    """Async console tracing works when OTel is not installed."""
    _patch_no_otel(mocker)
    expected = 3

    async def add(a, b):
        return a + b

    result = await AsyncTracer.trace(add, (1, 2), {})
    assert result == expected


def test_sync_trace_error_without_otel(mocker):
    """Exceptions propagate correctly without OTel (no _trace_span_error)."""
    _patch_no_otel(mocker)

    msg = "boom"

    def fail():
        raise ValueError(msg)

    with pytest.raises(ValueError, match="boom"):
        Tracer.trace(fail, (), {})


async def test_async_trace_error_without_otel(mocker):
    """Exceptions propagate correctly in async path without OTel."""
    _patch_no_otel(mocker)

    msg = "async boom"

    async def fail():
        raise ValueError(msg)

    with pytest.raises(ValueError, match="async boom"):
        await AsyncTracer.trace(fail, (), {})


def test_otel_true_raises_without_otel(mocker):
    """Otel=True raises ImportError when OTel is not installed and global is unset."""
    _patch_no_otel(mocker)
    # Set OTEL_FLAG to None (unset) so local otel=True can activate
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=None)

    def noop():
        pass

    with pytest.raises(ImportError, match="pip install omniray"):
        Tracer.trace(noop, (), {}, otel=True)


async def test_async_otel_true_raises_without_otel(mocker):
    """Async: otel=True raises ImportError when OTel is not installed and global is unset."""
    _patch_no_otel(mocker)
    # Set OTEL_FLAG to None (unset) so local otel=True can activate
    mocker.patch("omniray.tracing.tracers.OTEL_FLAG", new=None)

    async def noop():
        pass

    with pytest.raises(ImportError, match="pip install omniray"):
        await AsyncTracer.trace(noop, (), {}, otel=True)
