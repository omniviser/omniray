"""Shared fixtures for all omniray tests."""

import re

import pytest
from omniray.tracing.flags import _default_flags_cache

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


@pytest.fixture
def strip_ansi():
    """Return a callable that strips ANSI SGR escape codes (e.g. ``\\x1b[31m``) from text."""
    return lambda text: _ANSI_RE.sub("", text)
