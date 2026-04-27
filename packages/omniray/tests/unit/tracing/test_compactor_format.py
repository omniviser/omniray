"""Output format tests for compacted summaries.

Strip ANSI codes when asserting structural content (line count, indent,
labels), but keep raw output for color assertions. Drives the public
note_entry/note_exit_success API and patches the module logger to capture
the rendered text.
"""

import re

import pytest
from colorama import Fore, Style
from omniray.tracing import compactor as compactor_module
from omniray.tracing.compactor import Compactor
from omniray.tracing.thresholds import Thresholds

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

THRESHOLD = 3
STREAK_OF_FOUR = 4
STREAK_OF_FIVE = 5
EXPECTED_PER_CALL_LINES = 4  # 2 calls x (start + end) at below-threshold count


def _strip(text: str) -> str:
    return _ANSI.sub("", text)


def _rendered(mock_logger):
    return [c.args[0] % c.args[1:] for c in mock_logger.info.call_args_list]


@pytest.fixture
def compactor() -> Compactor:
    return Compactor(Thresholds(compact=True, compact_threshold=THRESHOLD))


def test_summary_emits_four_lines_when_extras_present(mocker, compactor):
    """Size + RSS data emit four lines: start, count, time, memory."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")
    for _ in range(STREAK_OF_FOUR):
        compactor.note_entry("op", 1)
        compactor.note_exit_success("op", 1, 2.0, input_size_mb=0.1, rss_current_mb=50.0)
    compactor.note_entry("flush", 1)
    compactor.note_exit_success("flush", 1, 1.0)

    rendered = [_strip(r) for r in _rendered(mock_logger)]
    # Continuation lines (time/memory) carry no span name, so we look for
    # them directly rather than filter by the span name.
    assert any(r.endswith(" op") and "┌─" in r for r in rendered)
    assert any(f"x{STREAK_OF_FOUR}" in r and r.endswith(" op") for r in rendered)
    assert any("time:" in r for r in rendered)
    assert any("memory:" in r for r in rendered)


def test_summary_skips_memory_line_when_no_extras(mocker, compactor):
    """Without size/rss data the streak emits only three lines: start, count, time."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")
    for _ in range(STREAK_OF_FIVE):
        compactor.note_entry("op", 0)
        compactor.note_exit_success("op", 0, 1.0)
    compactor.note_entry("flush", 0)
    compactor.note_exit_success("flush", 0, 1.0)

    rendered = [_strip(r) for r in _rendered(mock_logger)]
    assert any("┌─" in r and r.endswith(" op") for r in rendered)
    assert any(f"x{STREAK_OF_FIVE}" in r and r.endswith(" op") for r in rendered)
    assert any("time:" in r for r in rendered)
    assert not any("memory:" in r for r in rendered)


def test_summary_count_is_red(mocker, compactor):
    """The streak count always wears bright red — repetition itself is a perf signal."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")
    for _ in range(STREAK_OF_FOUR):
        compactor.note_entry("op", 0)
        compactor.note_exit_success("op", 0, 1.0)
    compactor.note_entry("flush", 0)
    compactor.note_exit_success("flush", 0, 1.0)

    rendered = _rendered(mock_logger)
    count_marker = f"x{STREAK_OF_FOUR}"
    count_line = next(r for r in rendered if count_marker in r)
    assert Fore.RED + Style.BRIGHT + count_marker in count_line


def test_continuation_indent_preserves_ancestor_pipes():
    """Nested depth keeps ancestor pipes; own leaf marker blanked out."""
    pipe = compactor_module.profilers.PIPE
    nested_depth = 3
    assert compactor_module._continuation_indent(0) == "   "
    assert compactor_module._continuation_indent(1) == pipe + "   "
    assert compactor_module._continuation_indent(nested_depth) == pipe * nested_depth + "   "


def test_below_threshold_renders_per_call_pairs(mocker, compactor):
    """count < threshold uses approximate per-call rendering (avg duration)."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")
    compactor.note_entry("op", 0)
    compactor.note_exit_success("op", 0, 1.0)
    compactor.note_entry("op", 0)
    compactor.note_exit_success("op", 0, 3.0)
    compactor.note_entry("flush", 0)
    compactor.note_exit_success("flush", 0, 1.0)

    rendered = [_strip(r) for r in _rendered(mock_logger)]
    op_lines = [r for r in rendered if r.endswith("op")]
    assert len(op_lines) == EXPECTED_PER_CALL_LINES
    end_lines = [r for r in op_lines if "(" in r and "ms)" in r]
    # Both end lines render the average duration (2.00ms) — exact per-call
    # timings are lost once a streak forms.
    assert all("2.00ms" in r for r in end_lines)
