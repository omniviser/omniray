"""Tests for DiscoveryConfig._is_excluded() method.

This method checks if a file/directory matches any exclude pattern using fnmatch. It checks both the
filename and all directory parts in the path.
"""

from pathlib import Path

import pytest
from omniwrap.config import DiscoveryConfig


def test_excludes_venv_directory():
    """Test that .venv directory is excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/.venv/lib/foo.py")

    assert config._is_excluded(py_file) is True


def test_excludes_pycache_directory():
    """Test that __pycache__ directory is excluded."""
    config = DiscoveryConfig()
    py_file = Path("/src/__pycache__/mod.py")

    assert config._is_excluded(py_file) is True


def test_excludes_git_directory():
    """Test that .git directory is excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/.git/hooks/pre-commit")

    assert config._is_excluded(py_file) is True


def test_excludes_deeply_nested_in_excluded_directory():
    """Test that files deep inside excluded directories are still excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/src/.venv/deep/nested/file.py")

    assert config._is_excluded(py_file) is True


@pytest.mark.parametrize(
    "excluded_dir",
    [".venv", "__pycache__", ".git", ".hg", ".pytest_cache"],
)
def test_all_default_excluded_directories(excluded_dir):
    """Test that all default excluded directories work."""
    config = DiscoveryConfig()
    py_file = Path(f"/project/{excluded_dir}/some/file.py")

    assert config._is_excluded(py_file) is True


def test_excludes_init_files():
    """Test that __init__.py files are excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/src/__init__.py")

    assert config._is_excluded(py_file) is True


def test_excludes_main_files():
    """Test that __main__.py files are excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/src/__main__.py")

    assert config._is_excluded(py_file) is True


def test_allows_regular_files():
    """Test that regular Python files are not excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/src/module.py")

    assert config._is_excluded(py_file) is False


def test_allows_normal_directories():
    """Test that normal directories are not excluded."""
    config = DiscoveryConfig()
    py_file = Path("/project/src/utils/helpers.py")

    assert config._is_excluded(py_file) is False


def test_custom_directory_pattern():
    """Test that custom directory patterns can be added."""
    default_config = DiscoveryConfig()
    config = DiscoveryConfig(exclude=default_config.exclude | {"tests"})
    py_file = Path("/project/tests/test_foo.py")

    assert config._is_excluded(py_file) is True


def test_custom_file_pattern_with_wildcard():
    """Test that custom wildcard patterns work."""
    default_config = DiscoveryConfig()
    config = DiscoveryConfig(exclude=default_config.exclude | {"test_*.py"})
    py_file = Path("/src/test_utils.py")

    assert config._is_excluded(py_file) is True


def test_wildcard_pattern_no_match():
    """Test that wildcard patterns don't match when they shouldn't."""
    default_config = DiscoveryConfig()
    config = DiscoveryConfig(exclude=default_config.exclude | {"test_*.py"})
    py_file = Path("/src/utils_test.py")

    assert config._is_excluded(py_file) is False


@pytest.mark.parametrize(
    ("pattern", "filename", "expected"),
    [
        pytest.param("test_*.py", "test_module.py", True, id="test_prefix_matches"),
        pytest.param("test_*.py", "module_test.py", False, id="test_prefix_no_match"),
        pytest.param("*_test.py", "module_test.py", True, id="test_suffix_matches"),
        pytest.param("*_test.py", "test_module.py", False, id="test_suffix_no_match"),
        pytest.param("conftest.py", "conftest.py", True, id="exact_match"),
        pytest.param("conftest.py", "my_conftest.py", False, id="exact_no_match"),
    ],
)
def test_various_wildcard_patterns(pattern, filename, *, expected):
    """Test various wildcard pattern matching scenarios."""
    default_config = DiscoveryConfig()
    config = DiscoveryConfig(exclude=default_config.exclude | {pattern})
    py_file = Path(f"/src/{filename}")

    assert config._is_excluded(py_file) is expected
