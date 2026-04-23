"""Configuration system for omniwrap module.

Reads ``[tool.omniwrap]`` of the nearest ``pyproject.toml``. The shared
``pyproject.toml`` loading primitives live in :mod:`omniwrap.pyproject`
so other ecosystem libraries can reuse them.

Error behaviour: any failure (missing file, malformed TOML, wrong types
in :class:`RawConfig`) is logged at ``WARNING`` and :meth:`DiscoveryConfig.from_pyproject`
returns defaults. Direct construction of :class:`RawConfig` with invalid
types still raises :class:`RawConfig.ConfigError` — that's the developer-facing
contract of the raw dataclass.
"""

import logging
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from omniwrap.pyproject import load_pyproject_config

logger = logging.getLogger(__name__)


@dataclass
class RawConfig:
    """Raw configuration from pyproject.toml [tool.omniwrap] section."""

    class ConfigError(Exception):
        """Raised when configuration in pyproject.toml is invalid."""

    paths: list[str] | None = None
    exclude: list[str] | None = None
    skip_wrap: list[str] | None = None

    def __post_init__(self) -> None:
        """Validate types after initialization."""
        self._validate_list_of_strings("paths", self.paths)
        self._validate_list_of_strings("exclude", self.exclude)
        self._validate_list_of_strings("skip_wrap", self.skip_wrap)

    def _validate_list_of_strings(self, name: str, value: list[str] | None) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            msg = f"{name} must be a list, got {type(value).__name__}"
            raise self.ConfigError(msg)
        for item in value:
            if not isinstance(item, str):
                msg = f"{name} must contain only strings, got {type(item).__name__}"
                raise self.ConfigError(msg)


@dataclass(frozen=True)
class DiscoveryConfig:
    """Immutable configuration for module discovery.

    Example pyproject.toml:
        [tool.omniwrap]
        paths = ["src", "app"]
        exclude = ["tests", "scripts", "data"]

    Example usage:
        # Load from pyproject.toml (or defaults if missing / malformed)
        config = DiscoveryConfig.from_pyproject()

        # Explicit defaults
        config = DiscoveryConfig()
    """

    paths: tuple[Path, ...] = (Path(),)
    exclude: frozenset[str] = frozenset(
        {
            ".venv",
            "__pycache__",
            ".git",
            ".hg",
            ".pytest_cache",
            "__init__.py",
            "__main__.py",
            "asgi.py",
            "wsgi.py",
        }
    )
    skip_wrap: frozenset[str] = frozenset()

    def should_import(self, py_file: Path) -> bool:
        """Check if file should be imported based on exclusion rules.

        Returns:
            True if file should be imported, False if excluded
        """
        if self._is_omniwrap_package(py_file):
            return False
        return not self._is_excluded(py_file)

    @staticmethod
    def _is_omniwrap_package(py_file: Path) -> bool:
        """Check if file is part of this package itself.

        This prevents recursive instrumentation by excluding the omniwrap package from being
        discovered and instrumented.
        """
        return "omniwrap" in py_file.parts

    def _is_excluded(self, py_file: Path) -> bool:
        """Check if file/directory matches any exclude pattern.

        Uses fnmatch for both file names and directory names in path.
        """
        return any(
            fnmatch(py_file.name, pattern) or any(fnmatch(part, pattern) for part in py_file.parts)
            for pattern in self.exclude
        )

    @classmethod
    def from_pyproject(cls, pyproject_path: Path | None = None) -> "DiscoveryConfig":
        """Load configuration from pyproject.toml."""
        raw = load_pyproject_config(
            RawConfig,
            ("omniwrap",),
            pyproject_path=pyproject_path,
            log=logger,
        )
        if raw is None:
            return cls()
        default_config = cls()
        return cls(
            paths=cls._merge_paths(raw, default_config),
            exclude=cls._merge_excludes(raw, default_config),
            skip_wrap=cls._merge_skip_wrap(raw),
        )

    @staticmethod
    def _merge_paths(raw_config: RawConfig, default_config: "DiscoveryConfig") -> tuple[Path, ...]:
        """Merge user-configured paths with defaults.

        Empty list paths=[] is treated as "use defaults".
        """
        if raw_config.paths:  # None or empty list -> use defaults
            return tuple(DiscoveryConfig._resolve_path(p) for p in raw_config.paths)
        return default_config.paths

    @staticmethod
    def _merge_excludes(raw_config: RawConfig, default_config: "DiscoveryConfig") -> frozenset[str]:
        """Merge user-configured exclusions with defaults."""
        if raw_config.exclude:
            return default_config.exclude | frozenset(raw_config.exclude)
        return default_config.exclude

    @staticmethod
    def _merge_skip_wrap(raw_config: RawConfig) -> frozenset[str]:
        """Convert user-configured method exclusions to frozenset."""
        if raw_config.skip_wrap:
            return frozenset(raw_config.skip_wrap)
        return frozenset()

    @staticmethod
    def _resolve_path(path_str: str) -> Path:
        """Resolve a path string to an absolute Path object."""
        path = Path(path_str)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()
