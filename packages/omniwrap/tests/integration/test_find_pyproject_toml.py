"""Integration tests for ``DiscoveryConfig.from_pyproject`` end-to-end flow.

Low-level pyproject primitives (``_find_pyproject_toml``, ``_load_section``,
``_build_raw_config``, ``load_pyproject_config``) are covered in
``tests/unit/test_pyproject.py``. The tests here exercise the full
``pyproject.toml`` → ``RawConfig`` → ``DiscoveryConfig`` pipeline with real
files on disk.
"""

import logging

import pytest
from omniwrap.config import DiscoveryConfig

pytestmark = pytest.mark.integration


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


def test_invalid_toml_syntax_warns_and_returns_defaults(tmp_path, caplog):
    """Malformed TOML → WARNING logged, defaults returned. Never raises.

    Previously this raised ``TOMLDecodeError`` — behaviour now unified with
    omniray: broken config never crashes the host app.
    """
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.omniwrap\n")  # Missing closing bracket

    with caplog.at_level(logging.WARNING, logger="omniwrap.config"):
        config = DiscoveryConfig.from_pyproject(pyproject)

    assert config == DiscoveryConfig()
    assert "Failed to parse pyproject.toml" in caplog.text


def test_invalid_types_warn_and_return_defaults(tmp_path, caplog):
    """Wrong field types → WARNING logged, defaults returned. Never raises."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.omniwrap]\npaths = "not-a-list"\n')

    with caplog.at_level(logging.WARNING, logger="omniwrap.config"):
        config = DiscoveryConfig.from_pyproject(pyproject)

    assert config == DiscoveryConfig()
    assert "Invalid [tool.omniwrap] config" in caplog.text
    assert "must be a list" in caplog.text


def test_no_tool_section_returns_defaults(create_pyproject):
    """Projects may have pyproject.toml for other tools but not configure omniwrap."""
    pyproject_path = create_pyproject(include_tool_section=False)

    config = DiscoveryConfig.from_pyproject(pyproject_path)

    assert config == DiscoveryConfig()


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
