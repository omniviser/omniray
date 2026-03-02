"""Tests for Wrapper._normalize_wrappers() method."""

from omniwrap.wrapper import Wrapper


def test_single_callable(mocker):
    """Single callable should be duplicated to (func, func) pair."""
    func = mocker.MagicMock(name="func")

    result = Wrapper._normalize_wrappers((func,))

    assert result == [(func, func)]


def test_tuple(mocker):
    """Tuple should be kept as-is."""
    sync = mocker.MagicMock(name="sync")
    async_ = mocker.MagicMock(name="async")

    result = Wrapper._normalize_wrappers(((sync, async_),))

    assert result == [(sync, async_)]


def test_multiple_callables(mocker):
    """Multiple callables should each become (func, func) pairs."""
    w1 = mocker.MagicMock(name="w1")
    w2 = mocker.MagicMock(name="w2")

    result = Wrapper._normalize_wrappers((w1, w2))

    assert result == [(w1, w1), (w2, w2)]


def test_multiple_tuples(mocker):
    """Multiple tuples should be kept as-is."""
    s1 = mocker.MagicMock(name="s1")
    a1 = mocker.MagicMock(name="a1")
    s2 = mocker.MagicMock(name="s2")
    a2 = mocker.MagicMock(name="a2")

    result = Wrapper._normalize_wrappers(((s1, a1), (s2, a2)))

    assert result == [(s1, a1), (s2, a2)]


def test_mixed(mocker):
    """Mix of callable and tuple should be normalized correctly."""
    w1 = mocker.MagicMock(name="w1")
    s2 = mocker.MagicMock(name="s2")
    a2 = mocker.MagicMock(name="a2")

    result = Wrapper._normalize_wrappers((w1, (s2, a2)))

    assert result == [(w1, w1), (s2, a2)]


def test_empty():
    """Empty input should return empty list."""
    result = Wrapper._normalize_wrappers(())

    assert result == []


def test_none_in_tuple(mocker):
    """None in a tuple should be preserved (async-only or sync-only)."""
    async_ = mocker.MagicMock(name="async")

    result = Wrapper._normalize_wrappers(((None, async_),))

    assert result == [(None, async_)]
