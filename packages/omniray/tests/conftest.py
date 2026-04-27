"""Shared fixtures for all omniray tests."""

import re

import pytest
from omniray.tracing.compactor import Compactor
from omniray.tracing.flags import _default_flags_cache
from omniray.tracing.thresholds import Thresholds
from omniray.tracing.tracers import Tracer

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(autouse=True)
def _clear_flags_cache():
    """Clear cached default flags between tests.

    Tests that monkeypatch OTEL_FLAG need a fresh cache, otherwise the cached TraceFlags from a
    previous test (with a different OTEL_FLAG value) leaks.
    """
    _default_flags_cache.clear()
    yield
    _default_flags_cache.clear()


@pytest.fixture(autouse=True)
def _disable_compaction(monkeypatch):
    """Swap in a disabled compactor by default.

    Most tracer tests assert per-call rendering (profilers.log_span_success
    called once per span). Tests covering compaction itself swap in their
    own ``Compactor`` with ``Thresholds(compact=True)``.
    """
    monkeypatch.setattr(Tracer, "compactor", Compactor(Thresholds(compact=False)))


@pytest.fixture
def strip_ansi():
    """Return a callable that strips ANSI SGR escape codes (e.g. ``\\x1b[31m``) from text."""
    return lambda text: _ANSI_RE.sub("", text)
