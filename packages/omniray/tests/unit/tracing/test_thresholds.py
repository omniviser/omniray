"""Tests for omniray.tracing.thresholds.

Delegated responsibilities:
- Walk-up / VCS stop / malformed TOML / unknown keys are tested in
  ``packages/omniwrap/tests/unit/test_pyproject.py`` (framework side).
- Here we verify omniray-specific behaviour: the ``[tool.omniray]`` section
  path, the triple/scalar validation rules, and that ``Thresholds.from_pyproject``
  silently falls back to defaults (with a WARNING) on any error.
"""

import logging

import pytest
from omniray.tracing.thresholds import RawThresholds, Thresholds


@pytest.fixture(autouse=True)
def _restore_omniray_propagate():
    """Ensure the ``omniray.tracing`` logger propagates so ``caplog`` can see records.

    ``setup_console_handler`` flips ``propagate=False`` once enabled, and the flag
    leaks between tests because loggers live in the ``logging`` module globals.
    """
    logger = logging.getLogger("omniray.tracing")
    prior = logger.propagate
    logger.propagate = True
    try:
        yield
    finally:
        logger.propagate = prior


def test_raw_thresholds_default_all_none():
    raw = RawThresholds()
    assert raw.size is None
    assert raw.size_big_tag_mb is None
    assert raw.duration_slow_tag_ms is None


def test_raw_thresholds_triple_wrong_type_raises():
    with pytest.raises(RawThresholds.ConfigError, match="size must be a list"):
        RawThresholds(size="foo")  # type: ignore[arg-type]


def test_raw_thresholds_triple_wrong_length_raises():
    with pytest.raises(RawThresholds.ConfigError, match="3 elements"):
        RawThresholds(size=[1, 2])


def test_raw_thresholds_triple_non_numeric_raises():
    with pytest.raises(RawThresholds.ConfigError, match="must contain numbers"):
        RawThresholds(size=[1, "bad", 3])  # type: ignore[list-item]


def test_raw_thresholds_triple_bool_rejected():
    """``bool`` is a subclass of int but semantically wrong here."""
    with pytest.raises(RawThresholds.ConfigError, match="must contain numbers"):
        RawThresholds(size=[1, True, 3])


def test_raw_thresholds_scalar_wrong_type_raises():
    with pytest.raises(RawThresholds.ConfigError, match="size_big_tag_mb must be numeric"):
        RawThresholds(size_big_tag_mb="foo")  # type: ignore[arg-type]


def test_raw_thresholds_scalar_bool_rejected():
    with pytest.raises(RawThresholds.ConfigError, match="must be numeric"):
        RawThresholds(size_big_tag_mb=True)  # type: ignore[arg-type]


def test_defaults_when_no_pyproject(tmp_path, monkeypatch):
    """Missing pyproject.toml → defaults. ``.git`` sentinel stops walk-up."""
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    assert Thresholds.from_pyproject() == Thresholds()


def test_parses_full_config(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.omniray]
size = [0.01, 0.5, 5.0]
size_big_tag_mb = 3
rss = [50, 200, 800]
rss_delta = [0.5, 5.0, 50.0]
duration_ms = [2, 20, 200]
duration_slow_tag_ms = 500
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = Thresholds.from_pyproject()
    assert result.size_mb == (0.01, 0.5, 5.0)
    assert result.size_big_tag_mb == 3.0
    assert result.rss_mb == (50.0, 200.0, 800.0)
    assert result.rss_delta_mb == (0.5, 5.0, 50.0)
    assert result.duration_ms == (2.0, 20.0, 200.0)
    assert result.duration_slow_tag_ms == 500.0


def test_partial_override_keeps_defaults(tmp_path, monkeypatch):
    """Fields absent from TOML keep their defaults."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.omniray]\nsize = [0.01, 0.5, 5.0]\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = Thresholds.from_pyproject()
    defaults = Thresholds()
    assert result.size_mb == (0.01, 0.5, 5.0)
    assert result.rss_mb == defaults.rss_mb
    assert result.rss_delta_mb == defaults.rss_delta_mb
    assert result.size_big_tag_mb == defaults.size_big_tag_mb


def test_empty_section_uses_defaults(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[tool.omniray]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert Thresholds.from_pyproject() == Thresholds()


def test_explicit_path_bypasses_walk_up(tmp_path):
    """Passing ``pyproject_path`` skips the cwd walk-up entirely."""
    pyproject = tmp_path / "custom.toml"
    pyproject.write_text("[tool.omniray]\nsize_big_tag_mb = 42\n", encoding="utf-8")
    result = Thresholds.from_pyproject(pyproject)
    assert result.size_big_tag_mb == 42.0


def test_nonexistent_explicit_path_falls_back(tmp_path):
    result = Thresholds.from_pyproject(tmp_path / "nope.toml")
    assert result == Thresholds()


def test_malformed_toml_warns_and_falls_back(tmp_path, monkeypatch, caplog):
    (tmp_path / "pyproject.toml").write_text("[tool.omniray\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.WARNING, logger="omniray.tracing"):
        result = Thresholds.from_pyproject()
    assert result == Thresholds()
    assert "Failed to parse pyproject.toml" in caplog.text


def test_wrong_type_warns_and_falls_back(tmp_path, monkeypatch, caplog):
    (tmp_path / "pyproject.toml").write_text('[tool.omniray]\nsize = "foo"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.WARNING, logger="omniray.tracing"):
        result = Thresholds.from_pyproject()
    assert result == Thresholds()
    assert "Invalid [tool.omniray] config" in caplog.text
    assert "must be a list" in caplog.text


def test_wrong_length_warns_and_falls_back(tmp_path, monkeypatch, caplog):
    (tmp_path / "pyproject.toml").write_text("[tool.omniray]\nsize = [1, 2]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.WARNING, logger="omniray.tracing"):
        result = Thresholds.from_pyproject()
    assert result == Thresholds()
    assert "3 elements" in caplog.text


def test_scalar_wrong_type_warns_and_falls_back(tmp_path, monkeypatch, caplog):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.omniray]\nduration_slow_tag_ms = "foo"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.WARNING, logger="omniray.tracing"):
        result = Thresholds.from_pyproject()
    assert result == Thresholds()
    assert "must be numeric" in caplog.text


def test_unknown_keys_warn_but_proceed(tmp_path, monkeypatch, caplog):
    """Unknown keys → WARNING + other fields still applied."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.omniray]\nsize = [1, 2, 3]\nbogus = 42\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.WARNING, logger="omniray.tracing"):
        result = Thresholds.from_pyproject()
    assert result.size_mb == (1.0, 2.0, 3.0)
    assert "Unknown config keys" in caplog.text
    assert "bogus" in caplog.text
