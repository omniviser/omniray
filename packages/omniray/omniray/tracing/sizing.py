"""Deep memory sizing of arbitrary Python objects."""

from __future__ import annotations

import logging

from pympler.asizeof import asizeof

logger = logging.getLogger("omniray.tracing")

_BYTES_PER_MB = 1024 * 1024


def measure_size_mb(value: object) -> float | None:
    """Return deep size of *value* in MB, or ``None`` when skipped/unavailable.

    Returns ``None`` for ``None`` inputs and when ``asizeof`` raises — tracing
    must never break the traced application.
    """
    if value is None:
        return None
    try:
        return asizeof(value) / _BYTES_PER_MB
    except Exception:  # noqa: BLE001
        logger.debug("omniray: asizeof failed", exc_info=True)
        return None
