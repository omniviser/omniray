"""End-to-end tests for streak compaction.

Drives a real ``@trace()`` decorator plus the real omniray.tracing logger
(via ``omniray_caplog``). Real ``pympler``/``psutil`` measurements run
end-to-end. The Tracer's compactor is swapped per-test for one with the
desired Thresholds — no module-level patching needed.
"""

from __future__ import annotations

import pytest
from colorama import Fore, Style
from omniray.decorators import trace
from omniray.tracing import flags as flags_module
from omniray.tracing.compactor import Compactor
from omniray.tracing.thresholds import Thresholds
from omniray.tracing.tracers import Tracer

REPETITIONS_HOT = 10
REPETITIONS_WORK = 5
REPETITIONS_PER_CALL = 4


@pytest.fixture
def _enable_compaction(monkeypatch):
    monkeypatch.setattr(
        Tracer,
        "compactor",
        Compactor(Thresholds(compact=True, compact_threshold=3)),
    )


@pytest.fixture
def _disable_compaction(monkeypatch):
    monkeypatch.setattr(
        Tracer,
        "compactor",
        Compactor(Thresholds(compact=False)),
    )


def _enable_flags(monkeypatch, **flag_values: bool) -> None:
    """Patch module-level flag constants and clear resolver cache."""
    defaults = {
        "CONSOLE_LOG_FLAG": False,
        "LOG_INPUT_FLAG": False,
        "LOG_OUTPUT_FLAG": False,
        "LOG_INPUT_SIZE_FLAG": False,
        "LOG_OUTPUT_SIZE_FLAG": False,
        "LOG_RSS_FLAG": False,
    }
    defaults.update(flag_values)
    for name, value in defaults.items():
        monkeypatch.setattr(f"omniray.tracing.flags.{name}", value)
    monkeypatch.setattr(flags_module, "_default_flags_cache", {})
    monkeypatch.setattr("omniray.tracing.tracers.OTEL_FLAG", False)


@pytest.mark.usefixtures("_enable_compaction")
def test_repeated_leaf_collapses_to_summary_line(monkeypatch, omniray_caplog):
    """10 identical sibling calls collapse to one summary instead of N entries."""
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True)
    plain, _raw = omniray_caplog

    @trace()
    def hot():
        return 1

    @trace()
    def flush_marker():
        return 0

    for _ in range(REPETITIONS_HOT):
        hot()
    flush_marker()  # different sibling → flush hot streak

    lines = plain()
    summary_lines = [line for line in lines if "x10" in line and "hot" in line]
    assert len(summary_lines) == 1
    end_lines = [line for line in lines if "└─ (" in line and "hot" in line]
    assert end_lines == []


@pytest.mark.usefixtures("_enable_compaction")
def test_summary_includes_aggregated_size_and_rss(monkeypatch, omniray_caplog):
    """With size/rss flags on, summary contains Sum-in/Sum-out/rss/peak."""
    _enable_flags(
        monkeypatch,
        CONSOLE_LOG_FLAG=True,
        LOG_INPUT_SIZE_FLAG=True,
        LOG_OUTPUT_SIZE_FLAG=True,
        LOG_RSS_FLAG=True,
    )
    plain, _raw = omniray_caplog

    @trace()
    def work(_payload):
        return [0] * 1000

    @trace()
    def flush_marker():
        return 0

    payload = [0] * 100
    for _ in range(REPETITIONS_WORK):
        work(payload)
    flush_marker()

    lines = plain()
    memory_lines = [line for line in lines if "memory:" in line]
    assert len(memory_lines) >= 1
    memory_line = memory_lines[0]
    assert "Σin:" in memory_line
    assert "Σout:" in memory_line
    assert "rss:" in memory_line
    assert "peak:" in memory_line


@pytest.mark.usefixtures("_disable_compaction")
def test_compaction_disabled_emits_per_call_lines(monkeypatch, omniray_caplog):
    """compact=False reverts to legacy per-call rendering, one end-line per call."""
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True)
    plain, _raw = omniray_caplog

    @trace()
    def hot():
        return 1

    for _ in range(REPETITIONS_PER_CALL):
        hot()

    lines = plain()
    end_lines = [line for line in lines if "└─ (" in line and "hot" in line]
    assert len(end_lines) == REPETITIONS_PER_CALL
    summary_lines = [line for line in lines if "x4" in line]
    assert summary_lines == []


@pytest.mark.usefixtures("_enable_compaction")
def test_streak_count_rendered_in_red(monkeypatch, omniray_caplog):
    """Streak count carries bright-red ANSI codes in raw (non-stripped) output."""
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True)
    _plain, raw = omniray_caplog

    @trace()
    def hot():
        return 1

    @trace()
    def flush_marker():
        return 0

    for _ in range(REPETITIONS_PER_CALL):
        hot()
    flush_marker()

    raw_lines = raw()
    red_count_lines = [line for line in raw_lines if Fore.RED + Style.BRIGHT + "x4" in line]
    assert len(red_count_lines) == 1
