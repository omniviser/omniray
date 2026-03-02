"""Shared fixtures for e2e tests."""

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


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
