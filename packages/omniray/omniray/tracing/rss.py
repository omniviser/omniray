"""Resident Set Size sampling of the current process."""

from __future__ import annotations

import logging
import os
import sys

import psutil

try:
    import resource as _resource  # Unix only
except ImportError:  # pragma: no cover — Windows path
    _resource = None

logger = logging.getLogger("omniray.tracing")

_BYTES_PER_MB = 1024 * 1024
_PROCESS = psutil.Process(os.getpid())
# On Linux ru_maxrss is in KB; on macOS in bytes. (POSIX leaves unit unspecified.)
_MAXRSS_TO_BYTES = 1 if sys.platform == "darwin" else 1024


def _current_process() -> psutil.Process:
    """Return cached ``psutil.Process``, refreshed when pid changes (post-fork).

    In pre-fork server setups (gunicorn/uvicorn ``--workers``, Django) the
    master imports omniray before forking, so the cached ``_PROCESS`` points
    at the master pid. After fork each worker must see its own pid.
    """
    global _PROCESS  # noqa: PLW0603 — singleton refreshed on fork (pid change)
    pid = os.getpid()
    if _PROCESS.pid != pid:
        _PROCESS = psutil.Process(pid)
    return _PROCESS


def read_rss_mb() -> float | None:
    """Return current process RSS in MB, or ``None`` when measurement fails.

    Tracing must never break the traced app — any psutil error is caught and
    logged at debug level.
    """
    try:
        return _current_process().memory_info().rss / _BYTES_PER_MB
    except Exception:  # noqa: BLE001
        logger.debug("omniray: psutil memory_info failed", exc_info=True)
        return None


def read_peak_rss_mb() -> float | None:
    """Return peak RSS since process start in MB (``None`` on failure / Windows).

    Uses ``resource.getrusage(RUSAGE_SELF).ru_maxrss``. Unit differs by platform:
    Linux returns kilobytes, macOS returns bytes — normalized via
    ``_MAXRSS_TO_BYTES``. Not available on Windows (``resource`` missing).
    """
    if _resource is None:
        return None
    try:
        return (
            _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
            * _MAXRSS_TO_BYTES
            / _BYTES_PER_MB
        )
    except Exception:  # noqa: BLE001
        logger.debug("omniray: getrusage failed", exc_info=True)
        return None
