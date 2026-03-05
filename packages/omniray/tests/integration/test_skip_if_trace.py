"""E2E tests for skip_if on @trace() decorator.

Covers sync/async functions and instance methods. Uses real OTel InMemorySpanExporter — no mocks.
"""

import pytest
from omniray.decorators import trace

# ── Functions ─────────────────────────────────────────────────────────


def test_sync_skip_if_true_no_spans(span_exporter):
    """When skip_if returns True, no OTel span is created."""

    @trace(skip_if=lambda x: x == "skip")
    def my_func(x):
        return f"result_{x}"

    result = my_func("skip")

    assert result == "result_skip"
    assert len(span_exporter.get_finished_spans()) == 0


def test_sync_skip_if_false_creates_span(span_exporter):
    """When skip_if returns False, a real OTel span is exported."""

    @trace(skip_if=lambda x: x == "skip")
    def my_func(x):
        return f"result_{x}"

    result = my_func("trace_me")

    assert result == "result_trace_me"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert "my_func" in spans[0].name


@pytest.mark.asyncio
async def test_async_skip_if_true_no_spans(span_exporter):
    """Async: when skip_if returns True, no OTel span is created."""

    @trace(skip_if=lambda x: x == "skip")
    async def my_async_func(x):
        return f"result_{x}"

    result = await my_async_func("skip")

    assert result == "result_skip"
    assert len(span_exporter.get_finished_spans()) == 0


@pytest.mark.asyncio
async def test_async_skip_if_false_creates_span(span_exporter):
    """Async: when skip_if returns False, a real OTel span is exported."""

    @trace(skip_if=lambda x: x == "skip")
    async def my_async_func(x):
        return f"result_{x}"

    result = await my_async_func("trace_me")

    assert result == "result_trace_me"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert "my_async_func" in spans[0].name


# ── Instance methods ──────────────────────────────────────────────────


def test_method_skip_if_skips(span_exporter):
    """@trace(skip_if=...) on method: self is passed to predicate, no span created."""

    class Service:
        @trace(skip_if=lambda _self, x: x == "skip")
        def process(self, x):
            return f"result_{x}"

    result = Service().process("skip")

    assert result == "result_skip"
    assert len(span_exporter.get_finished_spans()) == 0


def test_method_skip_if_traces(span_exporter):
    """@trace(skip_if=...) on method: predicate returns False, span created."""

    class Service:
        @trace(skip_if=lambda _self, x: x == "skip")
        def process(self, x):
            return f"result_{x}"

    result = Service().process("trace_me")

    assert result == "result_trace_me"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert "process" in spans[0].name
