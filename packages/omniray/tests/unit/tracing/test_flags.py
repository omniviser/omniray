"""Unit tests for flag resolution — resolve_flag(), _env_flag(), and caching."""

from omniray.tracing.flags import _env_flag, resolve_flag, resolve_trace_flags

# ── resolve_flag ──────────────────────────────────────────────────────


def test_resolve_flag_global_false_is_kill_switch():
    """Global=False always returns False regardless of local."""
    assert resolve_flag(global_flag=False, local_flag=None) is False
    assert resolve_flag(global_flag=False, local_flag=True) is False
    assert resolve_flag(global_flag=False, local_flag=False) is False


def test_resolve_flag_global_true_defaults_to_true():
    """Global=True returns True when local is None."""
    assert resolve_flag(global_flag=True, local_flag=None) is True


def test_resolve_flag_global_true_local_overrides():
    """Global=True allows local to override in either direction."""
    assert resolve_flag(global_flag=True, local_flag=True) is True
    assert resolve_flag(global_flag=True, local_flag=False) is False


def test_resolve_flag_global_none_defaults_to_false():
    """Global=None returns False when local is also None."""
    assert resolve_flag(global_flag=None, local_flag=None) is False


def test_resolve_flag_global_none_local_decides():
    """Global=None defers to local."""
    assert resolve_flag(global_flag=None, local_flag=True) is True
    assert resolve_flag(global_flag=None, local_flag=False) is False


# ── _env_flag ─────────────────────────────────────────────────────────


def test_env_flag_unset(monkeypatch):
    """Unset env var returns None."""
    monkeypatch.delenv("TEST_TRISTATE", raising=False)
    assert _env_flag("TEST_TRISTATE") is None


def test_env_flag_true_values(monkeypatch):
    """True-ish values return True."""
    for val in ("true", "True", "TRUE", "1", "yes", "YES"):
        monkeypatch.setenv("TEST_TRISTATE", val)
        assert _env_flag("TEST_TRISTATE") is True


def test_env_flag_false_values(monkeypatch):
    """Non-true values return False (not None)."""
    for val in ("false", "0", "no", "anything"):
        monkeypatch.setenv("TEST_TRISTATE", val)
        assert _env_flag("TEST_TRISTATE") is False


# ── resolve_trace_flags caching ──────────────────────────────────────


def test_resolve_trace_flags_cache_returns_same_object():
    """Second call with all-None locals returns cached singleton."""
    kwargs = {"log": None, "log_input": None, "log_output": None, "otel": None, "otel_flag": None}
    first = resolve_trace_flags(**kwargs)
    second = resolve_trace_flags(**kwargs)
    assert first is second
