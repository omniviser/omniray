"""E2E tests for skip_if on create_trace_wrapper().

Covers sync/async functions, instance methods (via wrapt), and error paths. Uses real OTel
InMemorySpanExporter — no mocks.
"""

import pytest
import wrapt
from omniray.decorators import create_trace_wrapper
from opentelemetry.trace import StatusCode

# ── Functions ─────────────────────────────────────────────────────────


def test_sync_skip_if_true_no_spans(span_exporter):
    """Sync wrapper: skip_if=True bypasses tracing entirely."""
    sync_wrapper, _ = create_trace_wrapper(skip_if=lambda x: x == "skip")

    def wrapped_func(x):
        return f"result_{x}"

    result = sync_wrapper(wrapped_func, None, ("skip",), {})

    assert result == "result_skip"
    assert len(span_exporter.get_finished_spans()) == 0


def test_sync_skip_if_false_creates_span(span_exporter):
    """Sync wrapper: skip_if=False goes through full tracing pipeline."""
    sync_wrapper, _ = create_trace_wrapper(skip_if=lambda x: x == "skip")

    def wrapped_func(x):
        return f"result_{x}"

    result = sync_wrapper(wrapped_func, None, ("trace_me",), {})

    assert result == "result_trace_me"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert "wrapped_func" in spans[0].name


@pytest.mark.asyncio
async def test_async_skip_if_true_no_spans(span_exporter):
    """Async wrapper: skip_if=True bypasses tracing entirely."""
    _, async_wrapper = create_trace_wrapper(skip_if=lambda x: x == "skip")

    async def wrapped_func(x):
        return f"result_{x}"

    result = await async_wrapper(wrapped_func, None, ("skip",), {})

    assert result == "result_skip"
    assert len(span_exporter.get_finished_spans()) == 0


@pytest.mark.asyncio
async def test_async_skip_if_false_creates_span(span_exporter):
    """Async wrapper: skip_if=False goes through full tracing pipeline."""
    _, async_wrapper = create_trace_wrapper(skip_if=lambda x: x == "skip")

    async def wrapped_func(x):
        return f"result_{x}"

    result = await async_wrapper(wrapped_func, None, ("trace_me",), {})

    assert result == "result_trace_me"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert "wrapped_func" in spans[0].name


# ── Instance methods (via wrapt) ──────────────────────────────────────


def test_method_skip_if_no_self_in_args(span_exporter):
    """Wrapt wrapper: skip_if receives args WITHOUT self (wrapt strips it to instance)."""
    sync_wrapper, _ = create_trace_wrapper(skip_if=lambda x: x == "skip")

    class Service:
        def process(self, x):
            return f"result_{x}"

    wrapt.wrap_function_wrapper(Service, "process", sync_wrapper)

    result = Service().process("skip")

    assert result == "result_skip"
    assert len(span_exporter.get_finished_spans()) == 0


def test_method_skip_if_false_traces(span_exporter):
    """Wrapt wrapper: skip_if returns False on method, span created."""
    sync_wrapper, _ = create_trace_wrapper(skip_if=lambda x: x == "skip")

    class Service:
        def process(self, x):
            return f"result_{x}"

    wrapt.wrap_function_wrapper(Service, "process", sync_wrapper)

    result = Service().process("trace_me")

    assert result == "result_trace_me"
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert "process" in spans[0].name


# ── Error path ────────────────────────────────────────────────────────


def test_exception_produces_error_span(span_exporter):
    """When traced function raises, span is exported with ERROR status."""
    sync_wrapper, _ = create_trace_wrapper()

    error_msg = "boom"

    def failing_func():
        raise ValueError(error_msg)

    with pytest.raises(ValueError, match="boom"):
        sync_wrapper(failing_func, None, (), {})

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code == StatusCode.ERROR
