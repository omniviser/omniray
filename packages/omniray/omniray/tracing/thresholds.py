"""Load threshold configuration from ``pyproject.toml``.

Uses omniwrap's mini-framework (:mod:`omniwrap.pyproject`) for file walk-up,
section loading, and validation infrastructure. omniray contributes only the
field shape, validators, and normalization.

Section path: ``[tool.omniray]`` — flat, all threshold keys directly under it.
Any failure (missing file, malformed TOML, invalid types) is logged at
``WARNING`` and defaults are returned — tracing must never break the host
application.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from omniwrap.pyproject import load_pyproject_config

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger("omniray.tracing")

_TRIPLE_LEN = 3


@dataclass
class RawThresholds:
    """Raw threshold values from ``[tool.omniray]``."""

    class ConfigError(Exception):
        """Raised when threshold configuration in pyproject.toml is invalid."""

    size: list[float] | None = None
    size_big_tag_mb: float | None = None
    rss: list[float] | None = None
    rss_delta: list[float] | None = None
    duration_ms: list[float] | None = None
    duration_slow_tag_ms: float | None = None

    def __post_init__(self) -> None:
        """Validate types after initialization."""
        self._validate_triple("size", self.size)
        self._validate_scalar("size_big_tag_mb", self.size_big_tag_mb)
        self._validate_triple("rss", self.rss)
        self._validate_triple("rss_delta", self.rss_delta)
        self._validate_triple("duration_ms", self.duration_ms)
        self._validate_scalar("duration_slow_tag_ms", self.duration_slow_tag_ms)

    def _validate_triple(self, name: str, value: list[float] | None) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            msg = f"{name} must be a list, got {type(value).__name__}"
            raise self.ConfigError(msg)
        if len(value) != _TRIPLE_LEN:
            msg = f"{name} must have {_TRIPLE_LEN} elements, got {len(value)}"
            raise self.ConfigError(msg)
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                msg = f"{name} must contain numbers, got {type(item).__name__}"
                raise self.ConfigError(msg)

    def _validate_scalar(self, name: str, value: float | None) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            msg = f"{name} must be numeric, got {type(value).__name__}"
            raise self.ConfigError(msg)


@dataclass(frozen=True)
class Thresholds:
    """Immutable color thresholds for trace-line values.

    Example pyproject.toml:
        [tool.omniray]
        size = [0.1, 1, 10]
        rss = [100, 500, 1000]

    Example usage:
        # Load from pyproject.toml (or defaults if missing / malformed)
        thresholds = Thresholds.from_pyproject()

        # Explicit defaults
        thresholds = Thresholds()
    """

    size_mb: tuple[float, float, float] = (0.1, 1.0, 10.0)
    rss_mb: tuple[float, float, float] = (100.0, 500.0, 1000.0)
    rss_delta_mb: tuple[float, float, float] = (1.0, 10.0, 100.0)
    duration_ms: tuple[float, float, float] = (1.0, 10.0, 100.0)
    duration_slow_tag_ms: float = 200.0
    size_big_tag_mb: float = 10.0

    @classmethod
    def from_pyproject(cls, pyproject_path: Path | None = None) -> Thresholds:
        """Load thresholds from pyproject.toml; WARNING + defaults on any error."""
        raw = load_pyproject_config(
            RawThresholds,
            ("omniray",),
            pyproject_path=pyproject_path,
            log=logger,
        )
        if raw is None:
            return cls()
        defaults = cls()
        return cls(
            size_mb=cls._to_triple(raw.size, defaults.size_mb),
            rss_mb=cls._to_triple(raw.rss, defaults.rss_mb),
            rss_delta_mb=cls._to_triple(raw.rss_delta, defaults.rss_delta_mb),
            duration_ms=cls._to_triple(raw.duration_ms, defaults.duration_ms),
            duration_slow_tag_ms=cls._to_scalar(
                raw.duration_slow_tag_ms, defaults.duration_slow_tag_ms
            ),
            size_big_tag_mb=cls._to_scalar(raw.size_big_tag_mb, defaults.size_big_tag_mb),
        )

    @staticmethod
    def _to_triple(
        value: list[float] | None, default: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        """Convert a validated raw list to a typed triple, or return ``default``."""
        if value is None:
            return default
        return (float(value[0]), float(value[1]), float(value[2]))

    @staticmethod
    def _to_scalar(value: float | None, default: float) -> float:
        """Convert a validated raw scalar to float, or return ``default``."""
        if value is None:
            return default
        return float(value)
