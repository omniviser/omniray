"""Tests for streak-compaction of repeated leaf calls."""

import pytest
from omniray.tracing import compactor as compactor_module
from omniray.tracing.compactor import Compactor
from omniray.tracing.thresholds import Thresholds

THRESHOLD = 3
BELOW_THRESHOLD = 2
ABOVE_THRESHOLD = 5
STREAK_OF_FOUR = 4
LINES_PER_BELOW_THRESHOLD_CALL = 2  # start + end pair per below-threshold call


@pytest.fixture
def compactor() -> Compactor:
    """Fresh Compactor with compaction enabled and threshold=3 per test."""
    return Compactor(Thresholds(compact=True, compact_threshold=THRESHOLD))


def _rendered(mock_logger):
    return [c.args[0] % c.args[1:] for c in mock_logger.info.call_args_list]


def test_below_threshold_emits_each_call(mocker, compactor):
    """Streak count < threshold → render each call as start+end pair."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    compactor.note_entry("leaf", 1)
    compactor.note_exit_success("leaf", 1, 1.0)
    compactor.note_entry("leaf", 1)
    compactor.note_exit_success("leaf", 1, 2.0)
    compactor.note_entry("other", 1)  # different name → flush prior streak
    compactor.note_exit_success("other", 1, 5.0)

    rendered = _rendered(mock_logger)
    # 2 leaf calls below threshold → 2 start lines + 2 end lines, then "other" deferred
    expected_leaf_lines = BELOW_THRESHOLD * LINES_PER_BELOW_THRESHOLD_CALL
    assert sum("leaf" in r for r in rendered) == expected_leaf_lines


def test_above_threshold_emits_summary(mocker, compactor):
    """Streak count >= threshold → single summary line replaces all calls."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    for _ in range(ABOVE_THRESHOLD):
        compactor.note_entry("leaf", 1)
        compactor.note_exit_success("leaf", 1, 1.0)
    compactor.note_entry("other", 1)  # flush
    compactor.note_exit_success("other", 1, 1.0)

    rendered = _rendered(mock_logger)
    leaf_lines = [r for r in rendered if "leaf" in r]
    # one start line + one summary line for the compacted streak
    summary_pair_lines = 2
    assert len(leaf_lines) == summary_pair_lines
    assert any(f"x{ABOVE_THRESHOLD}" in r for r in leaf_lines)


def test_different_name_breaks_streak(mocker, compactor):
    """Sibling with different name flushes prior streak before starting new."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    for _ in range(STREAK_OF_FOUR):
        compactor.note_entry("a", 1)
        compactor.note_exit_success("a", 1, 1.0)
    compactor.note_entry("b", 1)  # break — flush a
    compactor.note_exit_success("b", 1, 1.0)
    compactor.note_entry("a", 1)  # new streak for a
    compactor.note_exit_success("a", 1, 1.0)

    rendered = _rendered(mock_logger)
    a_summaries = [r for r in rendered if "a" in r and f"x{STREAK_OF_FOUR}" in r]
    assert len(a_summaries) == 1


def test_parent_with_children_logs_normally(mocker, compactor):
    """Non-leaf (has children) is not compacted; child entry promotes parent."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    deferred_parent = compactor.note_entry("parent", 0)
    assert deferred_parent is True

    # Child entry → parent's start line gets logged retroactively
    deferred_child = compactor.note_entry("child", 1)
    assert deferred_child is True
    rendered = _rendered(mock_logger)
    assert any("parent" in r for r in rendered)

    compacted_child = compactor.note_exit_success("child", 1, 1.0)
    assert compacted_child is True

    compacted_parent = compactor.note_exit_success("parent", 0, 5.0)
    assert compacted_parent is False


def test_compact_disabled_returns_false(mocker):
    """compact=False → compactor is a no-op pass-through."""
    disabled = Compactor(Thresholds(compact=False))
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    assert disabled.note_entry("x", 0) is False
    assert disabled.note_exit_success("x", 0, 1.0) is False
    assert mock_logger.info.call_count == 0


def test_exit_without_entry_returns_false(compactor):
    """Defensive path: note_exit_success without prior note_entry → False."""
    assert compactor.note_exit_success("orphan", 0, 1.0) is False


def test_exit_with_streak_name_mismatch_flushes_and_starts_new(mocker, compactor):
    """Defensive desync: pending span_name differs from streak[depth] span_name.

    Manually corrupt the state (push pending with mismatched name) to
    exercise the flush-and-restart branch in note_exit_success.
    """
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    for _ in range(STREAK_OF_FOUR):
        compactor.note_entry("a", 0)
        compactor.note_exit_success("a", 0, 1.0)
    # Streak[0] now holds "a" with count=4. Manually push a "b" pending so
    # the next note_exit_success for "b" hits the mismatch branch.
    state = compactor._get_state()
    state.pending_stack.append(compactor_module._Pending(span_name="b", depth=0))
    compacted = compactor.note_exit_success("b", 0, 1.0)

    assert compacted is True  # absorbed into a fresh "b" streak
    rendered = [c.args[0] % c.args[1:] for c in mock_logger.info.call_args_list]
    assert any(f"x{STREAK_OF_FOUR}" in r and "a" in r for r in rendered)


def test_failure_flushes_streak_before_error(mocker, compactor):
    """note_exit_failure flushes pending streak so error not masked."""
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    for _ in range(STREAK_OF_FOUR):
        compactor.note_entry("a", 1)
        compactor.note_exit_success("a", 1, 1.0)
    compactor.note_entry("boom", 1)
    compactor.note_exit_failure(1)

    rendered = _rendered(mock_logger)
    assert any(f"x{STREAK_OF_FOUR}" in r and "a" in r for r in rendered)
