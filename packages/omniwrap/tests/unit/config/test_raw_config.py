"""Tests for RawConfig dataclass."""

import logging

import pytest
from omniwrap.config import RawConfig


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        pytest.param("paths", "src", "paths must be a list", id="paths_as_string"),
        pytest.param("paths", 123, "paths must be a list", id="paths_as_int"),
        pytest.param("exclude", "tests", "exclude must be a list", id="exclude_as_string"),
        pytest.param(
            "paths",
            [1, 2, 3],
            "paths must contain only strings",
            id="paths_with_int_elements",
        ),
        pytest.param(
            "exclude",
            [True, False],
            "exclude must contain only strings",
            id="exclude_with_bool_elements",
        ),
        pytest.param(
            "paths",
            ["src", None],
            "paths must contain only strings",
            id="paths_with_none_element",
        ),
        pytest.param(
            "skip_wrap",
            "to_pydantic",
            "skip_wrap must be a list",
            id="skip_wrap_as_string",
        ),
        pytest.param(
            "skip_wrap",
            [1, 2],
            "skip_wrap must contain only strings",
            id="skip_wrap_with_int_elements",
        ),
    ],
)
def test_invalid_types_raise_config_error(field, value, match):
    """Invalid types raise ConfigError with descriptive message."""
    with pytest.raises(RawConfig.ConfigError, match=match):
        RawConfig(**{field: value})


@pytest.mark.parametrize(
    ("paths", "exclude"),
    [
        pytest.param(None, None, id="none_values"),
        pytest.param([], [], id="empty_lists"),
    ],
)
def test_valid_values_pass_validation(paths, exclude):
    """None and empty lists pass validation."""
    config = RawConfig(paths=paths, exclude=exclude)

    assert config.paths == paths
    assert config.exclude == exclude


def test_from_dict_partial_config_fills_missing_with_none():
    """Dict with only some keys fills others with None."""
    config = RawConfig.from_dict({"paths": ["src"]})

    assert config.paths == ["src"]
    assert config.exclude is None


def test_from_dict_unknown_key_logs_warning(caplog):
    """Unknown keys trigger warning about possible typo."""
    with caplog.at_level(logging.WARNING, logger="omniwrap.config"):
        RawConfig.from_dict({"path": ["src"]})  # typo: 'path' instead of 'paths'

    assert "Unknown config keys" in caplog.text
    assert "path" in caplog.text
