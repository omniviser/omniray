"""Shared fixtures for E2E tests."""

import pytest
from omniwrap.config import DiscoveryConfig


@pytest.fixture
def sync_source():
    """Python source with a sync function."""
    return """
def greet(name):
    return f"Hello {name}"
"""


@pytest.fixture
def async_source():
    """Python source with an async function."""
    return """
async def fetch(url):
    return f"Fetched {url}"
"""


@pytest.fixture
def mixed_source():
    """Python source with both sync and async functions."""
    return """
def greet(name):
    return f"Hello {name}"

async def fetch(url):
    return f"Fetched {url}"
"""


def _make_sync_wrapper(label, calls):
    """Create a sync wrapper that records before/after in calls list."""

    def wrapper(wrapped, _instance, args, kwargs):
        calls.append(f"{label}_before")
        result = wrapped(*args, **kwargs)
        calls.append(f"{label}_after")
        return result

    return wrapper


def _make_async_wrapper(label, calls):
    """Create an async wrapper that records before/after in calls list."""

    async def wrapper(wrapped, _instance, args, kwargs):
        calls.append(f"{label}_before")
        result = await wrapped(*args, **kwargs)
        calls.append(f"{label}_after")
        return result

    return wrapper


@pytest.fixture
def calls():
    """Shared call recording list."""
    return []


@pytest.fixture
def sync_wrapper_factory(calls):
    """Factory for creating labeled sync wrappers sharing the calls list."""

    def factory(label):
        return _make_sync_wrapper(label, calls)

    return factory


@pytest.fixture
def async_wrapper_factory(calls):
    """Factory for creating labeled async wrappers sharing the calls list."""

    def factory(label):
        return _make_async_wrapper(label, calls)

    return factory


@pytest.fixture
def create_module(tmp_path, sys_path_context):
    """Create a temporary Python module and return its DiscoveryConfig."""

    def factory(source):
        pkg = tmp_path / "myapp"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "service.py").write_text(source)
        sys_path_context(tmp_path, "myapp")
        return DiscoveryConfig(paths=(tmp_path,), exclude=frozenset())

    return factory


@pytest.fixture
def create_modules(tmp_path, sys_path_context):
    """Create multiple temporary Python modules and return DiscoveryConfig."""

    def factory(sources: dict[str, str]):
        """Create modules from a dict of ``{"myapp/service.py": "...", ...}``."""
        pkg = tmp_path / "myapp"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("")
        for rel_path, source in sources.items():
            filepath = tmp_path / rel_path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(source)
        sys_path_context(tmp_path, "myapp")
        return DiscoveryConfig(paths=(tmp_path,), exclude=frozenset())

    return factory
