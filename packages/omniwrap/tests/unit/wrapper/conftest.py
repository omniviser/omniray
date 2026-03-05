"""Fixtures for wrapper tests."""

from types import ModuleType

import pytest


@pytest.fixture
def mock_wrappers(mocker):
    """Tuple of (sync_wrapper, async_wrapper)."""
    return (mocker.MagicMock(name="sync"), mocker.MagicMock(name="async"))


@pytest.fixture
def mock_wrappers_list(mock_wrappers):
    """List containing a single (sync_wrapper, async_wrapper) pair."""
    return [mock_wrappers]


@pytest.fixture
def test_module():
    """Sample module for testing."""
    return ModuleType("test_module")
