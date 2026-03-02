"""Tests for getting pyproject config methods."""

import logging
import tomllib

import pytest
from omniwrap.config import DiscoveryConfig

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("chdir_to_tmp")
def test_finds_pyproject_in_cwd(tmp_path):
    """Test that pyproject.toml in current directory is found.

    Most common case - running from project root.
    """
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n')

    result = DiscoveryConfig._find_pyproject_toml()

    assert result == pyproject


@pytest.mark.usefixtures("chdir_to_tmp")
def test_stops_search_at_git_directory(tmp_path):
    """Test that search stops at .git directory (VCS root).

    Following Black's approach - don't search above VCS root. This prevents
    finding unrelated pyproject.toml in parent projects (monorepo case).
    """
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / ".git").mkdir()

    result = DiscoveryConfig._find_pyproject_toml()

    assert result is None


@pytest.mark.usefixtures("chdir_to_tmp")
def test_no_pyproject_returns_defaults(tmp_path):
    """Test that missing pyproject.toml returns default configuration.

    New projects or projects without pyproject.toml should work with defaults.
    """
    (tmp_path / ".git").mkdir()  # Stop the search

    config = DiscoveryConfig.from_pyproject()

    assert config == DiscoveryConfig()


@pytest.mark.usefixtures("chdir_to_tmp")
def test_full_configuration_merged(create_pyproject):
    """Test that full configuration is properly merged with defaults.

    Integration test - verifies the complete flow from file to config object.
    """
    pyproject_path = create_pyproject(
        paths=["src"],
        exclude=["tests", "test_*.py"],
    )

    config = DiscoveryConfig.from_pyproject(pyproject_path)

    assert len(config.paths) == 1
    assert "tests" in config.exclude
    assert "test_*.py" in config.exclude
    assert ".venv" in config.exclude  # Default preserved


def test_invalid_toml_syntax_raises_decode_error(tmp_path):
    """Test that malformed TOML raises TOMLDecodeError.

    Users should get a clear error when their TOML syntax is invalid.
    """
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.omniwrap\n")  # Missing closing bracket

    with pytest.raises(tomllib.TOMLDecodeError):
        DiscoveryConfig.from_pyproject(pyproject)


def test_no_tool_section_logs_debug(create_pyproject, caplog):
    """Test that missing [tool.omniwrap] section logs debug message.

    Projects may have pyproject.toml for other tools but not configure omniwrap.
    """
    pyproject_path = create_pyproject(include_tool_section=False)

    with caplog.at_level(logging.DEBUG, logger="omniwrap.config"):
        config = DiscoveryConfig.from_pyproject(pyproject_path)

    assert config == DiscoveryConfig()
    assert "No [tool.omniwrap] section" in caplog.text


@pytest.mark.usefixtures("chdir_to_tmp")
def test_skip_wrap_loaded_from_pyproject(create_pyproject):
    """Test that skip_wrap is correctly loaded from pyproject.toml.

    Integration test — verifies the full flow from TOML file to config object for the skip_wrap
    field.
    """
    pyproject_path = create_pyproject(
        skip_wrap=["to_pydantic", "to_dict"],
    )

    config = DiscoveryConfig.from_pyproject(pyproject_path)

    assert config.skip_wrap == frozenset({"to_pydantic", "to_dict"})
    assert config.skip_wrap == frozenset({"to_pydantic", "to_dict"})


def test_returns_none_at_filesystem_root(tmp_path, monkeypatch):
    """Test that search returns None when reaching filesystem root.

    Edge case: no pyproject.toml and no VCS directory anywhere in path.
    """
    monkeypatch.chdir(tmp_path)
    # No .git, no pyproject.toml - will traverse up to root

    result = DiscoveryConfig._find_pyproject_toml()

    assert result is None
