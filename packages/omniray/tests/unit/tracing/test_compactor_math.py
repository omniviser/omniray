"""Math correctness tests for the streak aggregator.

These tests exercise ``_Streak.add`` and the ``_Streak._sum`` / ``_Streak._max`` static helpers
directly, without going through the public note_* API. They verify that
sum/mean/max/min computations remain accurate under varied inputs and
mixed ``None`` values for optional extras.
"""

import pytest
from omniray.tracing import compactor


def test_streak_aggregates_duration_stats():
    """total_ms = sum, max_ms = max, min_ms = min across all add() calls."""
    streak = compactor._Streak(span_name="x", depth=0)
    durations = [1.5, 0.5, 4.25, 2.0, 0.1]
    for d in durations:
        streak.add(d)
    assert streak.count == len(durations)
    assert streak.total_ms == pytest.approx(sum(durations))
    assert streak.max_ms == pytest.approx(max(durations))
    assert streak.min_ms == pytest.approx(min(durations))


def test_streak_sums_input_output_size():
    """Σin / Σout accumulate per-call values; None inputs leave that field alone."""
    streak = compactor._Streak(span_name="x", depth=0)
    streak.add(1.0, input_size_mb=0.5, output_size_mb=0.1)
    streak.add(1.0, input_size_mb=1.5, output_size_mb=None)
    streak.add(1.0, input_size_mb=2.0, output_size_mb=0.4)
    assert streak.total_input_mb == pytest.approx(4.0)
    assert streak.total_output_mb == pytest.approx(0.5)


def test_streak_aggregates_rss_max_and_delta_sum():
    """rss/peak track max observed, delta sums across the streak (signed)."""
    streak = compactor._Streak(span_name="x", depth=0)
    streak.add(1.0, rss_current_mb=100.0, rss_peak_mb=120.0, rss_delta_mb=+5.0)
    streak.add(1.0, rss_current_mb=110.0, rss_peak_mb=115.0, rss_delta_mb=-3.0)
    streak.add(1.0, rss_current_mb=105.0, rss_peak_mb=140.0, rss_delta_mb=+1.0)
    assert streak.max_rss_mb == pytest.approx(110.0)
    assert streak.max_rss_peak_mb == pytest.approx(140.0)
    assert streak.total_rss_delta_mb == pytest.approx(3.0)


def test_streak_extras_remain_none_when_never_set():
    """All-None extras across all calls → fields stay None (memory line skipped)."""
    streak = compactor._Streak(span_name="x", depth=0)
    streak.add(1.0)
    streak.add(2.0)
    assert streak.total_input_mb is None
    assert streak.total_output_mb is None
    assert streak.max_rss_mb is None
    assert streak.max_rss_peak_mb is None
    assert streak.total_rss_delta_mb is None


def test_accumulate_sum_handles_none():
    """Sum: None+None=None, mixed picks the value, both numeric adds."""
    assert compactor._Streak._sum(None, None) is None
    assert compactor._Streak._sum(None, 5.0) == pytest.approx(5.0)
    assert compactor._Streak._sum(3.0, None) == pytest.approx(3.0)
    assert compactor._Streak._sum(3.0, 5.0) == pytest.approx(8.0)


def test_accumulate_max_handles_none():
    """Max: None/None=None, mixed picks the value, both numeric picks max."""
    assert compactor._Streak._max(None, None) is None
    assert compactor._Streak._max(None, 5.0) == pytest.approx(5.0)
    assert compactor._Streak._max(3.0, None) == pytest.approx(3.0)
    assert compactor._Streak._max(3.0, 5.0) == pytest.approx(5.0)
    assert compactor._Streak._max(7.0, 5.0) == pytest.approx(7.0)
