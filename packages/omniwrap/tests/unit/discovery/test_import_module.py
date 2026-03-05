"""Tests for ModuleDiscovery._import_module.

The import mechanism must be resilient - one broken module should not
crash the entire discovery process. These tests verify that valid modules
are imported correctly, broken modules return None (not exceptions),
and proper logging helps with debugging import issues in production.
"""

import logging
from types import ModuleType

from omniwrap.discovery import ModuleDiscovery


def test_imports_existing_stdlib_module():
    """Test that existing standard library modules are imported successfully.

    Basic sanity check - if we can't import stdlib modules, nothing works.
    Verifies the happy path before testing error cases.
    """
    result = ModuleDiscovery._import_module("os")

    assert result is not None
    assert isinstance(result, ModuleType)
    assert result.__name__ == "os"


def test_returns_none_for_nonexistent_module():
    """Test that None is returned for modules that don't exist.

    Critical for resilience - discovery iterates many files, and some may
    not be valid modules. Returning None allows the loop to continue
    instead of crashing on the first bad file.
    """
    result = ModuleDiscovery._import_module("nonexistent_module_xyz_123")

    assert result is None


def test_returns_none_for_import_error(mocker):
    """Test that ImportError exceptions are caught and None is returned.

    Modules can fail to import for various reasons (missing dependencies, syntax errors in
    dependencies, circular imports). All should be caught to prevent one bad module from breaking
    the entire discovery.
    """
    mocker.patch(
        "omniwrap.discovery.importlib.import_module",
        side_effect=ImportError("Module not found"),
    )

    result = ModuleDiscovery._import_module("some_module")

    assert result is None


def test_logs_successful_import(caplog):
    """Test that successful imports are logged at DEBUG level.

    Logging helps debug which modules were discovered in production. Without this, it's hard to
    verify the discovery is working correctly.
    """
    with caplog.at_level(logging.DEBUG, logger="omniwrap.discovery"):
        ModuleDiscovery._import_module("os")

    assert "Discovered and imported: os" in caplog.text


def test_does_not_log_failed_import(caplog):
    """Test that failed imports do not produce success log messages.

    Prevents misleading logs - if import failed, we shouldn't log success.
    This catches bugs where logging happens before the actual import.
    """
    with caplog.at_level(logging.DEBUG, logger="omniwrap.discovery"):
        ModuleDiscovery._import_module("nonexistent_xyz")

    assert "Discovered and imported" not in caplog.text
