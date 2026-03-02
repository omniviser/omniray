"""Tests for DiscoveryConfig merge methods.

Key design decision: paths REPLACE defaults, but excludes and patterns are ADDED to
defaults. This ensures users don't accidentally lose critical exclusions like .venv.
"""

import pytest
from omniwrap.config import DiscoveryConfig, RawConfig


@pytest.mark.usefixtures("chdir_to_tmp")
def test_merge_paths_replaces_defaults():
    """Test that user-specified paths replace defaults entirely.

    Unlike excludes, paths don't merge - user paths completely replace
    the default (current directory).
    """
    raw_config = RawConfig(paths=["src", "app"])
    default_config = DiscoveryConfig()

    result = DiscoveryConfig._merge_paths(raw_config, default_config)

    expected_count = 2
    assert len(result) == expected_count
    assert all(p.is_absolute() for p in result)


def test_merge_excludes_adds_to_defaults():
    """Test that user excludes are added to defaults.

    Adding 'tests' should keep '.venv' and other defaults. This is the
    critical behavior - users shouldn't accidentally lose default exclusions.
    """
    raw_config = RawConfig(exclude=["tests"])
    default_config = DiscoveryConfig()

    result = DiscoveryConfig._merge_excludes(raw_config, default_config)

    assert "tests" in result
    assert ".venv" in result  # Default preserved


def test_merge_paths_with_empty_list_uses_defaults():
    """Test that empty paths list uses defaults.

    Empty paths would break discovery, so we treat None/[] as "use defaults".
    """
    raw_config = RawConfig(paths=[])
    default_config = DiscoveryConfig()

    result = DiscoveryConfig._merge_paths(raw_config, default_config)

    assert result == default_config.paths


def test_merge_excludes_with_empty_list_uses_defaults():
    """Test that empty exclude list uses defaults.

    Empty list means "no additions", use defaults.
    """
    raw_config = RawConfig(exclude=[])
    default_config = DiscoveryConfig()

    result = DiscoveryConfig._merge_excludes(raw_config, default_config)

    assert result == default_config.exclude


def test_merge_skip_wrap_converts_to_frozenset():
    """Test that skip_wrap list is converted to frozenset."""
    raw_config = RawConfig(skip_wrap=["to_pydantic", "to_dict"])

    result = DiscoveryConfig._merge_skip_wrap(raw_config)

    assert result == frozenset({"to_pydantic", "to_dict"})


def test_merge_skip_wrap_none_returns_empty():
    """Test that None skip_wrap returns empty frozenset."""
    raw_config = RawConfig(skip_wrap=None)

    result = DiscoveryConfig._merge_skip_wrap(raw_config)

    assert result == frozenset()


def test_merge_skip_wrap_empty_list_returns_empty():
    """Test that empty skip_wrap returns empty frozenset."""
    raw_config = RawConfig(skip_wrap=[])

    result = DiscoveryConfig._merge_skip_wrap(raw_config)

    assert result == frozenset()


def test_merge_paths_with_absolute_path_preserves_it(tmp_path):
    """Absolute paths skip cwd prepending and are only resolved."""
    raw_config = RawConfig(paths=[str(tmp_path)])
    default_config = DiscoveryConfig()

    result = DiscoveryConfig._merge_paths(raw_config, default_config)

    assert len(result) == 1
    assert result[0].is_absolute()
    assert result[0] == tmp_path.resolve()
