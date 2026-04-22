"""Unit tests for flag resolution — resolve_flag(), _env_flag(), and caching."""

import pytest
from omniray.tracing import flags as flags_module
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
    kwargs = {
        "log": None,
        "log_input": None,
        "log_output": None,
        "log_input_size": None,
        "log_output_size": None,
        "otel": None,
        "otel_flag": None,
    }
    first = resolve_trace_flags(**kwargs)
    second = resolve_trace_flags(**kwargs)
    assert first is second


# ── log_input_size / log_output_size resolution ───────────────────────

_BASE_KWARGS = {
    "log": None,
    "log_input": None,
    "log_output": None,
    "log_input_size": None,
    "log_output_size": None,
    "otel": None,
    "otel_flag": None,
}


@pytest.fixture
def _clear_flags_cache():
    flags_module._default_flags_cache.clear()
    yield
    flags_module._default_flags_cache.clear()


@pytest.mark.usefixtures("_clear_flags_cache")
def test_resolve_trace_flags_log_input_size_global_on(mocker):
    """LOG_INPUT_SIZE_FLAG=True with CONSOLE_LOG_FLAG=True yields log_input_size=True."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_SIZE_FLAG", new=True)
    result = resolve_trace_flags(**_BASE_KWARGS)
    assert result.log_input_size is True


@pytest.mark.usefixtures("_clear_flags_cache")
def test_resolve_trace_flags_log_input_size_gated_by_log(mocker):
    """LOG_INPUT_SIZE_FLAG=True with CONSOLE_LOG_FLAG=False is suppressed."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=False)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_SIZE_FLAG", new=True)
    result = resolve_trace_flags(**_BASE_KWARGS)
    assert result.log_input_size is False


@pytest.mark.usefixtures("_clear_flags_cache")
def test_resolve_trace_flags_log_output_size_per_function_override(mocker):
    """Local log_output_size=True overrides global=None when log is on."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_SIZE_FLAG", new=None)
    kwargs = {**_BASE_KWARGS, "log_output_size": True}
    result = resolve_trace_flags(**kwargs)
    assert result.log_output_size is True


@pytest.mark.usefixtures("_clear_flags_cache")
def test_resolve_trace_flags_log_output_size_global_on(mocker):
    """LOG_OUTPUT_SIZE_FLAG=True with CONSOLE_LOG_FLAG=True yields log_output_size=True."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_SIZE_FLAG", new=True)
    result = resolve_trace_flags(**_BASE_KWARGS)
    assert result.log_output_size is True


@pytest.mark.usefixtures("_clear_flags_cache")
def test_resolve_trace_flags_size_flags_default_false(mocker):
    """All size flags default to False when env vars unset."""
    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mocker.patch("omniray.tracing.flags.LOG_INPUT_SIZE_FLAG", new=None)
    mocker.patch("omniray.tracing.flags.LOG_OUTPUT_SIZE_FLAG", new=None)
    result = resolve_trace_flags(**_BASE_KWARGS)
    assert result.log_input_size is False
    assert result.log_output_size is False
