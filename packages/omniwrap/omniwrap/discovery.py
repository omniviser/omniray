"""Module discovery and import system.

This module provides the ModuleDiscovery class which finds and imports all application modules for
instrumentation.

Configuration is loaded from pyproject.toml [tool.omniwrap] section. See DiscoveryConfig class for
available options.
"""

import importlib
import logging
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

from omniwrap.config import DiscoveryConfig

logger = logging.getLogger(__name__)


class ModuleDiscovery:
    """Discovers and imports application modules."""

    @classmethod
    def discover(cls, config: DiscoveryConfig | None = None) -> list[ModuleType]:
        """Discover and import all Python modules based on configuration."""
        if config is None:
            config = DiscoveryConfig.from_pyproject()
        return [
            module
            for module_name in cls._discover_module_names(config)
            if (module := cls._import_module(module_name)) is not None
        ]

    @classmethod
    def _discover_module_names(cls, config: DiscoveryConfig) -> Iterator[str]:
        """Yield unique module names from configured paths."""
        for py_file, root_path in cls._iter_unique_files(config):
            if config.should_import(py_file) and (
                module_name := cls._convert_path_to_module_name(py_file, root_path)
            ):
                yield module_name

    @classmethod
    def _iter_unique_files(cls, config: DiscoveryConfig) -> Iterator[tuple[Path, Path]]:
        """Yield unique (py_file, root_path) tuples."""
        seen: set[Path] = set()
        for root_path in config.paths:
            for py_file in root_path.rglob("*.py"):
                resolved = py_file.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield py_file, root_path

    @classmethod
    def _import_module(cls, module_name: str) -> ModuleType | None:
        """Import module, return None on failure."""
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return None
        else:
            logger.debug("Discovered and imported: %s", module_name)
            return module

    @classmethod
    def _convert_path_to_module_name(cls, py_file: Path, root_path: Path) -> str | None:
        """Convert file path to Python module name."""
        try:
            relative_path = py_file.relative_to(root_path).with_suffix("")
            return ".".join(relative_path.parts)
        except ValueError:
            return None
