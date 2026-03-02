"""Tests for Wrapper._should_wrap() method."""

import pytest
from omniwrap.wrapper import Wrapper


def test_enabled_true_returns_true():
    """When enabled=True, should always return True."""
    assert Wrapper._should_wrap(enabled=True) is True


def test_enabled_false_returns_false():
    """When enabled=False, should always return False."""
    assert Wrapper._should_wrap(enabled=False) is False


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("true", id="true"),
        pytest.param("TRUE", id="TRUE"),
        pytest.param("True", id="True"),
        pytest.param("1", id="1"),
        pytest.param("yes", id="yes"),
        pytest.param("YES", id="YES"),
    ],
)
def test_env_truthy_values_return_true(monkeypatch, value):
    """Truthy OMNIWRAP values should return True."""
    monkeypatch.setenv("OMNIWRAP", value)
    assert Wrapper._should_wrap(enabled=None) is True


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("false", id="false"),
        pytest.param("0", id="0"),
        pytest.param("no", id="no"),
        pytest.param("", id="empty"),
        pytest.param("random", id="random"),
    ],
)
def test_env_falsy_values_return_false(monkeypatch, value):
    """Falsy OMNIWRAP values should return False."""
    monkeypatch.setenv("OMNIWRAP", value)
    assert Wrapper._should_wrap(enabled=None) is False


def test_env_unset_returns_false(monkeypatch):
    """When OMNIWRAP is not set, should return False (default)."""
    monkeypatch.delenv("OMNIWRAP", raising=False)
    assert Wrapper._should_wrap(enabled=None) is False
