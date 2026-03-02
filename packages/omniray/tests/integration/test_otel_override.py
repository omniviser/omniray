"""Integration tests for per-function OTel override via @trace(otel=True)."""

import pytest
from omniray.decorators import trace


@trace(otel=True)
def _important_function():
    return "result"


@trace(otel=True)
async def _important_async_function():
    return "async_result"


def test_trace_otel_true_creates_span_when_global_unset(span_exporter_otel_off):
    """@trace(otel=True) creates a real OTel span when OMNIRAY_OTEL is unset (None)."""
    result = _important_function()

    assert result == "result"
    spans = span_exporter_otel_off.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "_important_function"


@pytest.mark.asyncio
async def test_trace_async_otel_true_creates_span_when_global_unset(span_exporter_otel_off):
    """Async: @trace(otel=True) creates a real OTel span when OMNIRAY_OTEL is unset."""
    result = await _important_async_function()

    assert result == "async_result"
    spans = span_exporter_otel_off.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "_important_async_function"


def test_trace_default_no_span_when_global_unset(span_exporter_otel_off):
    """@trace() creates NO span when OMNIRAY_OTEL is unset (profiler only)."""

    @trace()
    def regular_function():
        return "result"

    result = regular_function()

    assert result == "result"
    spans = span_exporter_otel_off.get_finished_spans()
    assert len(spans) == 0


def test_trace_otel_false_no_span_when_global_on(span_exporter):
    """@trace(otel=False) suppresses span even when OMNIRAY_OTEL=true."""

    @trace(otel=False)
    def suppressed_function():
        return "result"

    result = suppressed_function()

    assert result == "result"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 0


def test_trace_otel_true_blocked_by_kill_switch(span_exporter_otel_kill_switch):
    """@trace(otel=True) creates NO span when OMNIRAY_OTEL=false (kill switch)."""

    @trace(otel=True)
    def important_function():
        return "result"

    result = important_function()

    assert result == "result"
    spans = span_exporter_otel_kill_switch.get_finished_spans()
    assert len(spans) == 0
