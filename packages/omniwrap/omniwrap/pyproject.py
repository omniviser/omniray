"""Mini framework for loading library settings from ``pyproject.toml``."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


def load_pyproject_config[T](
    raw_cls: type[T],
    section_path: Sequence[str],
    *,
    pyproject_path: Path | None = None,
    log: logging.Logger,
) -> T | None:
    """Load a library config section from ``pyproject.toml`` into a dataclass.

    Walks up from cwd (or from *pyproject_path* if given) to find the nearest
    ``pyproject.toml`` (stopping at VCS root), reads the nested
    ``[tool.<section_path>]`` section, and constructs *raw_cls* from it.
    Unknown keys in the section are dropped and logged as a typo warning on
    *log*. Missing values become dataclass defaults.

    Any failure — missing file, malformed TOML, ``OSError`` during read, or
    validation errors raised by the dataclass's ``__post_init__`` — is logged
    at ``WARNING`` on *log* and the function returns ``None``. Never raises.

    This is the recommended entry point for libraries following the
    two-dataclass pattern (``RawXxx`` + normalized ``Xxx``). The caller's
    top-level ``from_pyproject()`` classmethod wraps this and returns defaults
    when this returns ``None``.
    """
    try:
        data = _load_section(section_path, pyproject_path)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning(
            "Failed to parse pyproject.toml for [tool.%s]: %s",
            ".".join(section_path),
            exc,
        )
        return None
    if data is None:
        return None
    try:
        return _build_raw_config(raw_cls, data, log=log)
    except Exception as exc:  # noqa: BLE001 — catch any validation failure in __post_init__
        log.warning(
            "Invalid [tool.%s] config, using defaults: %s",
            ".".join(section_path),
            exc,
        )
        return None


def _find_pyproject_toml(start: Path | None = None) -> Path | None:
    """Find ``pyproject.toml`` by walking up from *start* (defaults to cwd).

    Uses Black's approach: stops at the first VCS root (``.git`` or ``.hg``)
    to avoid picking up an unrelated ``pyproject.toml`` higher in the tree —
    critical in monorepo layouts and when running from tempdirs.
    """
    directory = (start or Path.cwd()).resolve()
    while True:
        candidate = directory / "pyproject.toml"
        if candidate.exists():
            logger.debug("Found pyproject.toml at: %s", candidate)
            return candidate
        if (directory / ".git").exists() or (directory / ".hg").exists():
            logger.debug("Stopped at VCS root: %s", directory)
            return None
        parent = directory.parent
        if parent == directory:  # filesystem root
            return None
        directory = parent


def _load_section(
    section_path: Sequence[str],
    pyproject_path: Path | None = None,
) -> dict | None:
    """Load a nested ``[tool.<section_path>]`` section from ``pyproject.toml``.

    Returns ``None`` when the file is missing or the section is absent/empty.
    Raises :class:`tomllib.TOMLDecodeError` for malformed TOML and
    :class:`OSError` for read errors — caller (``load_pyproject_config``)
    catches those and converts to a warning-and-fallback.
    """
    if pyproject_path is None:
        pyproject_path = _find_pyproject_toml()
    if pyproject_path is None or not pyproject_path.exists():
        return None
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    current: object = data.get("tool", {})
    for key in section_path:
        if not isinstance(current, dict):
            return None
        current = current.get(key, {})
    if not isinstance(current, dict) or not current:
        return None
    return current


def _build_raw_config[T](
    raw_cls: type[T],
    data: dict,
    *,
    log: logging.Logger | None = None,
) -> T:
    """Construct a dataclass from a dict, warning about unknown keys.

    Unknown keys are dropped and logged at ``WARNING`` on *log* (or this
    module's logger when not given). Field-level type validation is the
    caller's responsibility — typically via ``__post_init__`` on the raw
    dataclass.

    *raw_cls* must be a dataclass; :class:`TypeError` is raised otherwise.
    """
    if not is_dataclass(raw_cls):
        msg = f"{raw_cls.__name__} must be a dataclass"
        raise TypeError(msg)
    known_keys = {f.name for f in fields(raw_cls)}
    unknown = set(data.keys()) - known_keys
    if unknown:
        (log or logger).warning(
            "Unknown config keys (possible typo?): %s", unknown
        )
    return raw_cls(**{k: v for k, v in data.items() if k in known_keys})
