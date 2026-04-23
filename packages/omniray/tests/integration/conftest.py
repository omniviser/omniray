"""Shared fixtures for e2e tests."""

import io
import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture
def omniray_caplog(strip_ansi):
    """Caplog-equivalent for the ``omniray.tracing`` logger.

    Pytest's built-in ``caplog`` attaches to the root logger, so it can't see
    records from ``omniray.tracing`` (which has ``propagate=False``). This
    fixture attaches a ``StringIO`` handler directly to that logger and
    yields ``(plain, raw)`` callables — unlike ``caplog``, these return
    already-formatted lines (not ``LogRecord`` objects). ``plain()`` strips
    ANSI escape codes; ``raw()`` preserves them for color assertions.
    """
    logger = logging.getLogger("omniray.tracing")
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.DEBUG)
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:

        def plain() -> list[str]:
            return [strip_ansi(line) for line in buf.getvalue().splitlines()]

        def raw() -> list[str]:
            return buf.getvalue().splitlines()

        yield plain, raw
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


@pytest.fixture
def span_exporter(monkeypatch):
    """Set up real OTel pipeline with InMemorySpanExporter."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    test_tracer = provider.get_tracer("test")

    # All tracing now goes through tracers module — only need to patch there
    monkeypatch.setattr("omniray.tracing.tracers.otel_tracer", test_tracer)
    monkeypatch.setattr("omniray.tracing.tracers.OTEL_FLAG", True)

    yield exporter

    provider.shutdown()


@pytest.fixture
def span_exporter_otel_off(monkeypatch):
    """OTel pipeline with global OTEL unset (None) — for testing per-function override.

    Uses ``None`` (not ``False``) because ``False`` is a kill switch that
    would block per-function ``otel=True`` overrides.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    test_tracer = provider.get_tracer("test")

    monkeypatch.setattr("omniray.tracing.tracers.otel_tracer", test_tracer)
    monkeypatch.setattr("omniray.tracing.tracers.OTEL_FLAG", None)

    yield exporter

    provider.shutdown()


@pytest.fixture
def span_exporter_otel_kill_switch(monkeypatch):
    """OTel pipeline with global OTEL kill switch (False) — blocks all OTel."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    test_tracer = provider.get_tracer("test")

    monkeypatch.setattr("omniray.tracing.tracers.otel_tracer", test_tracer)
    monkeypatch.setattr("omniray.tracing.tracers.OTEL_FLAG", False)

    yield exporter

    provider.shutdown()
