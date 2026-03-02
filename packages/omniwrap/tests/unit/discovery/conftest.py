"""Fixtures for discovery unit tests."""

from pathlib import Path

import pytest


@pytest.fixture
def mock_discovery_config(mocker):
    """Factory fixture for creating mock DiscoveryConfig with custom settings."""

    def _create_config(
        paths: list[Path] | None = None,
        *,
        should_import_returns: bool = True,
    ):
        config = mocker.Mock()
        config.paths = paths or []
        config.should_import = mocker.Mock(return_value=should_import_returns)
        return config

    return _create_config


@pytest.fixture
def sample_root_path(tmp_path: Path) -> Path:
    """Return a sample root path for path conversion tests."""
    return tmp_path / "src"


@pytest.fixture
def sample_py_file(sample_root_path: Path) -> Path:
    """Return a sample Python file path for tests."""
    sample_root_path.mkdir(parents=True, exist_ok=True)
    py_file = sample_root_path / "app" / "main.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text("# test module")
    return py_file
