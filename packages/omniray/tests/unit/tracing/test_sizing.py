"""Tests for omniray.tracing.sizing."""

import pytest
from omniray.tracing import sizing
from omniray.tracing.sizing import measure_size_mb


def test_measure_size_mb_none_returns_none():
    assert measure_size_mb(None) is None


def test_measure_size_mb_small_dict_returns_positive_float():
    result = measure_size_mb({"a": 1, "b": "x"})
    assert isinstance(result, float)
    assert 0 < result < 0.01


def test_measure_size_mb_bytes_5mb_returns_approx_5():
    payload = b"x" * (5 * 1024 * 1024)
    result = measure_size_mb(payload)
    assert result == pytest.approx(5.0, abs=0.01)


def test_measure_size_mb_catches_asizeof_exceptions(mocker):
    mocker.patch.object(sizing, "asizeof", side_effect=RuntimeError("boom"))
    mock_debug = mocker.patch.object(sizing.logger, "debug")

    result = measure_size_mb({})

    assert result is None
    mock_debug.assert_called_once()
    assert "asizeof failed" in mock_debug.call_args[0][0]


def test_measure_size_mb_tuple_of_args_kwargs():
    result = measure_size_mb(((1, 2), {"k": "v"}))
    assert isinstance(result, float)
    assert result > 0
