"""Tests for the pyproject mini-framework (``omniwrap.pyproject``)."""

import logging
import tomllib
from dataclasses import dataclass

import pytest
from omniwrap.pyproject import (
    _build_raw_config,
    _find_pyproject_toml,
    _load_section,
    load_pyproject_config,
)


@dataclass
class _Sample:
    """Sample raw dataclass used across tests."""

    name: str | None = None
    count: int | None = None

    def __post_init__(self) -> None:
        if self.count is not None and self.count < 0:
            msg = "count must be non-negative"
            raise ValueError(msg)


def test_find_pyproject_in_cwd(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert _find_pyproject_toml() == pyproject


def test_find_pyproject_walks_up_from_subdir(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert _find_pyproject_toml() == pyproject


def test_find_pyproject_accepts_start_argument(tmp_path):
    """*start* overrides cwd — useful for tests and explicit callers."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert _find_pyproject_toml(start=nested) == pyproject


def test_find_pyproject_stops_at_git_root(tmp_path, monkeypatch):
    """``.git`` stops the walk-up — prevents monorepo cross-talk."""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    nested = repo / "pkg"
    nested.mkdir()
    monkeypatch.chdir(nested)
    assert _find_pyproject_toml() is None


def test_find_pyproject_stops_at_hg_root(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".hg").mkdir()
    nested = repo / "pkg"
    nested.mkdir()
    monkeypatch.chdir(nested)
    assert _find_pyproject_toml() is None


def test_find_pyproject_returns_none_at_filesystem_root(tmp_path, monkeypatch, mocker):
    """No pyproject.toml and no VCS anywhere → traverse to root and return None."""
    monkeypatch.chdir(tmp_path)
    mocker.patch("omniwrap.pyproject.Path.exists", return_value=False)
    assert _find_pyproject_toml() is None


def test_load_section_returns_dict(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.myapp]\nname = "foo"\ncount = 3\n', encoding="utf-8"
    )
    assert _load_section(("myapp",), pyproject) == {"name": "foo", "count": 3}


def test_load_section_nested_keys(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.outer.inner]\nkey = "value"\n', encoding="utf-8"
    )
    assert _load_section(("outer", "inner"), pyproject) == {"key": "value"}


def test_load_section_missing_returns_none(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")
    assert _load_section(("myapp",), pyproject) is None


def test_load_section_empty_returns_none(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.myapp]\n", encoding="utf-8")
    assert _load_section(("myapp",), pyproject) is None


def test_load_section_intermediate_key_not_dict(tmp_path):
    """If a mid-path key holds a scalar (not a table), return None."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool]\nouter = "scalar"\n', encoding="utf-8")
    assert _load_section(("outer", "inner"), pyproject) is None


def test_load_section_no_file_returns_none(tmp_path, monkeypatch):
    """No pyproject.toml + no .git → walk reaches filesystem root → None."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    assert _load_section(("omniwrap",)) is None


def test_load_section_nonexistent_explicit_path(tmp_path):
    assert _load_section(("myapp",), tmp_path / "nope.toml") is None


def test_load_section_uses_cwd_when_path_none(tmp_path, monkeypatch):
    """Without *pyproject_path*, walk-up from cwd picks up the nearest file."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.myapp]\nname = "cwd"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert _load_section(("myapp",)) == {"name": "cwd"}


def test_load_section_malformed_toml_raises(tmp_path):
    """Malformed TOML propagates to the caller (``load_pyproject_config``)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.myapp\n", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        _load_section(("myapp",), pyproject)


def test_build_raw_config_happy_path(caplog):
    with caplog.at_level(logging.WARNING, logger="omniwrap.pyproject"):
        result = _build_raw_config(_Sample, {"name": "foo", "count": 3})
    assert result == _Sample(name="foo", count=3)
    assert caplog.text == ""


def test_build_raw_config_drops_unknown_keys(caplog):
    with caplog.at_level(logging.WARNING, logger="omniwrap.pyproject"):
        result = _build_raw_config(_Sample, {"name": "foo", "bogus": 1})
    assert result == _Sample(name="foo")
    assert "Unknown config keys" in caplog.text
    assert "bogus" in caplog.text


def test_build_raw_config_uses_provided_logger(caplog):
    custom = logging.getLogger("custom.test.logger")
    with caplog.at_level(logging.WARNING, logger="custom.test.logger"):
        _build_raw_config(_Sample, {"typo": 1}, log=custom)
    assert "Unknown config keys" in caplog.text


def test_build_raw_config_non_dataclass_raises():
    class NotADataclass:
        pass

    with pytest.raises(TypeError, match="must be a dataclass"):
        _build_raw_config(NotADataclass, {})


def test_build_raw_config_post_init_validation_propagates():
    """``__post_init__`` exceptions bubble up — caller catches in ``load_pyproject_config``."""
    with pytest.raises(ValueError, match="non-negative"):
        _build_raw_config(_Sample, {"count": -1})


def test_load_pyproject_config_happy_path(tmp_path, monkeypatch, caplog):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.myapp]\nname = "foo"\ncount = 3\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("test.myapp")
    with caplog.at_level(logging.WARNING, logger="test.myapp"):
        result = load_pyproject_config(_Sample, ("myapp",), log=logger)
    assert result == _Sample(name="foo", count=3)
    assert caplog.text == ""


def test_load_pyproject_config_explicit_path(tmp_path):
    pyproject = tmp_path / "custom.toml"
    pyproject.write_text('[tool.myapp]\nname = "bar"\n', encoding="utf-8")
    logger = logging.getLogger("test.myapp")
    result = load_pyproject_config(
        _Sample, ("myapp",), pyproject_path=pyproject, log=logger
    )
    assert result == _Sample(name="bar")


def test_load_pyproject_config_missing_file_returns_none(tmp_path, monkeypatch):
    """No pyproject.toml in cwd → None, no warning (legitimate case)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()  # stop walk-up
    logger = logging.getLogger("test.myapp")
    assert load_pyproject_config(_Sample, ("myapp",), log=logger) is None


def test_load_pyproject_config_missing_section_returns_none(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("test.myapp")
    assert load_pyproject_config(_Sample, ("myapp",), log=logger) is None


def test_load_pyproject_config_malformed_toml_warns_and_returns_none(
    tmp_path, monkeypatch, caplog
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.myapp\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("test.myapp")
    with caplog.at_level(logging.WARNING, logger="test.myapp"):
        result = load_pyproject_config(_Sample, ("myapp",), log=logger)
    assert result is None
    assert "Failed to parse pyproject.toml" in caplog.text
    assert "[tool.myapp]" in caplog.text


def test_load_pyproject_config_post_init_validation_warns_and_returns_none(
    tmp_path, monkeypatch, caplog
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.myapp]\ncount = -1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("test.myapp")
    with caplog.at_level(logging.WARNING, logger="test.myapp"):
        result = load_pyproject_config(_Sample, ("myapp",), log=logger)
    assert result is None
    assert "Invalid [tool.myapp] config" in caplog.text
    assert "non-negative" in caplog.text


def test_load_pyproject_config_unknown_keys_warn_but_proceed(
    tmp_path, monkeypatch, caplog
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.myapp]\nname = "foo"\nbogus = 1\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("test.myapp")
    with caplog.at_level(logging.WARNING, logger="test.myapp"):
        result = load_pyproject_config(_Sample, ("myapp",), log=logger)
    assert result == _Sample(name="foo")
    assert "Unknown config keys" in caplog.text
    assert "bogus" in caplog.text


def test_load_pyproject_config_os_error_warns(tmp_path, monkeypatch, mocker, caplog):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.myapp]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    mocker.patch(
        "omniwrap.pyproject.tomllib.load", side_effect=OSError("disk fail")
    )
    logger = logging.getLogger("test.myapp")
    with caplog.at_level(logging.WARNING, logger="test.myapp"):
        result = load_pyproject_config(_Sample, ("myapp",), log=logger)
    assert result is None
    assert "Failed to parse pyproject.toml" in caplog.text


def test_load_pyproject_config_nested_section_path(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.outer.inner]\nname = "nested"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("test.myapp")
    result = load_pyproject_config(
        _Sample, ("outer", "inner"), log=logger
    )
    assert result == _Sample(name="nested")


def test_load_pyproject_config_nonexistent_explicit_path_returns_none(tmp_path):
    logger = logging.getLogger("test.myapp")
    result = load_pyproject_config(
        _Sample,
        ("myapp",),
        pyproject_path=tmp_path / "nope.toml",
        log=logger,
    )
    assert result is None
