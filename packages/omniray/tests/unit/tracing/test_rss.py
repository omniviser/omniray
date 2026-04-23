"""Tests for omniray.tracing.rss."""

import psutil
import pytest
from omniray.tracing import rss
from omniray.tracing.rss import read_peak_rss_mb, read_rss_mb


def test_read_rss_mb_returns_positive_float():
    result = read_rss_mb()
    assert isinstance(result, float)
    assert result > 0


def test_read_rss_mb_catches_psutil_exceptions(mocker):
    fake_proc = mocker.MagicMock(spec=psutil.Process)
    fake_proc.memory_info.side_effect = RuntimeError("boom")
    mocker.patch.object(rss, "_current_process", return_value=fake_proc)
    mock_debug = mocker.patch.object(rss.logger, "debug")

    result = read_rss_mb()

    assert result is None
    mock_debug.assert_called_once()
    assert "psutil memory_info failed" in mock_debug.call_args[0][0]


def test_current_process_refreshes_when_pid_changes(mocker):
    """After fork the cached Process must be replaced with one matching getpid()."""
    stale = mocker.MagicMock(spec=psutil.Process)
    stale.pid = 1111
    fresh = mocker.MagicMock(spec=psutil.Process)
    fresh.pid = 2222
    mocker.patch.object(rss, "_PROCESS", stale)
    mocker.patch.object(rss.os, "getpid", return_value=2222)
    mock_ctor = mocker.patch.object(rss.psutil, "Process", return_value=fresh)

    result = rss._current_process()

    mock_ctor.assert_called_once_with(2222)
    assert result is fresh
    assert rss._PROCESS is fresh


def test_current_process_reuses_cache_when_pid_matches(mocker):
    """Same pid → cached Process returned without constructing a new one."""
    cached = mocker.MagicMock(spec=psutil.Process)
    cached.pid = 3333
    mocker.patch.object(rss, "_PROCESS", cached)
    mocker.patch.object(rss.os, "getpid", return_value=3333)
    mock_ctor = mocker.patch.object(rss.psutil, "Process")

    result = rss._current_process()

    mock_ctor.assert_not_called()
    assert result is cached


@pytest.mark.skipif(rss._resource is None, reason="requires POSIX resource module")
def test_read_peak_rss_mb_returns_positive_float():
    result = read_peak_rss_mb()
    assert isinstance(result, float)
    assert result > 0


def _fake_resource(mocker, ru_maxrss=0, getrusage_side_effect=None):
    """Return a mock stand-in for the ``resource`` module.

    Tests use this so ``_resource`` can be patched as a whole module on
    Windows, where ``import resource`` fails and ``rss._resource is None``.
    """
    fake = mocker.MagicMock()
    fake.RUSAGE_SELF = 0
    if getrusage_side_effect is not None:
        fake.getrusage.side_effect = getrusage_side_effect
    else:
        fake.getrusage.return_value = mocker.MagicMock(ru_maxrss=ru_maxrss)
    return fake


def test_read_peak_rss_mb_linux_unit_is_kb(mocker):
    """Linux path: ru_maxrss in KB → multiply by 1024 then divide by 1MB."""
    mocker.patch.object(rss, "_MAXRSS_TO_BYTES", 1024)
    mocker.patch.object(rss, "_resource", _fake_resource(mocker, ru_maxrss=2_000_000))
    result = read_peak_rss_mb()
    assert result == 2_000_000 * 1024 / (1024 * 1024)


def test_read_peak_rss_mb_macos_unit_is_bytes(mocker):
    """macOS path: ru_maxrss in bytes → / 1MB."""
    mocker.patch.object(rss, "_MAXRSS_TO_BYTES", 1)
    mocker.patch.object(rss, "_resource", _fake_resource(mocker, ru_maxrss=3_000_000_000))
    result = read_peak_rss_mb()
    assert result == 3_000_000_000 / (1024 * 1024)


def test_read_peak_rss_mb_catches_exceptions(mocker):
    mocker.patch.object(
        rss, "_resource", _fake_resource(mocker, getrusage_side_effect=RuntimeError("boom"))
    )
    mock_debug = mocker.patch.object(rss.logger, "debug")

    result = read_peak_rss_mb()

    assert result is None
    mock_debug.assert_called_once()
    assert "getrusage failed" in mock_debug.call_args[0][0]


def test_read_peak_rss_mb_returns_none_when_resource_unavailable(mocker):
    """On Windows ``resource`` import fails → _resource is None → read returns None."""
    mocker.patch.object(rss, "_resource", None)
    assert read_peak_rss_mb() is None
