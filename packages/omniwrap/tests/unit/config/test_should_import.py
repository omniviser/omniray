"""Tests for DiscoveryConfig.should_import() method.

The should_import() method is the main public API for file filtering. It combines three
checks (omniwrap package, excluded directories, excluded patterns) into one decision.
We test only the integration here - individual checks are tested in their own files.
"""

from pathlib import Path

from omniwrap.config import DiscoveryConfig


def test_allows_regular_python_file():
    """Test that regular Python files in user directories are allowed.

    This is the happy path - normal source files should pass all checks.
    If this fails, nothing gets instrumented.
    """
    config = DiscoveryConfig()
    py_file = Path("/project/src/module.py")

    assert config.should_import(py_file) is True


def test_excludes_omniwrap_package():
    """Test that files in omniwrap package are excluded.

    Prevents recursive instrumentation - omniwrap profiling itself would cause infinite loops.
    """
    config = DiscoveryConfig()
    py_file = Path("/libs/omniwrap/omniwrap/config.py")

    assert config.should_import(py_file) is False


def test_excludes_venv_directory():
    """Test that files in excluded directories are rejected.

    Virtual environments contain third-party code that shouldn't be instrumented.
    """
    config = DiscoveryConfig()
    py_file = Path("/project/.venv/lib/module.py")

    assert config.should_import(py_file) is False


def test_excludes_init_pattern():
    """Test that files matching excluded patterns are rejected.

    Init files typically contain only imports, not business logic worth profiling.
    """
    config = DiscoveryConfig()
    py_file = Path("/project/src/__init__.py")

    assert config.should_import(py_file) is False
