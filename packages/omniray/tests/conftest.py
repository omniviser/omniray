"""Shared fixtures for all omniray tests."""

import pytest
from omniray.tracing.flags import _default_flags_cache


@pytest.fixture(autouse=True)
def _clear_flags_cache():
    """Clear cached default flags between tests.

    Tests that monkeypatch OTEL_FLAG need a fresh cache, otherwise the cached TraceFlags from a
    previous test (with a different OTEL_FLAG value) leaks.
    """
    _default_flags_cache.clear()
    yield
    _default_flags_cache.clear()
