"""Integration tests — drive a real Tracer.trace() and assert end-to-end output.

Mocks span only the OS-level dependencies (size measurement, RSS reading)
and the logger sink. Everything in between — Tracer, compactor, profilers,
flag resolution — runs as in production. This catches regressions in the
glue between modules that pure unit tests miss.
"""

import re

import pytest
from omniray.tracing import tracers
from omniray.tracing.compactor import Compactor
from omniray.tracing.flags import TraceFlags
from omniray.tracing.thresholds import Thresholds

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
LEAF_REPETITIONS_DISABLED = 3
LEAF_REPETITIONS_COMPACTED = 10
LEAF_REPETITIONS_WITH_EXTRAS = 4


def _strip(text: str) -> str:
    return _ANSI.sub("", text)


def _rendered(mock_logger):
    return [c.args[0] % c.args[1:] for c in mock_logger.info.call_args_list]


def _flags(*, sizes: bool = False, rss: bool = False) -> TraceFlags:
    return TraceFlags(
        log=True,
        log_input=False,
        log_output=False,
        log_input_size=sizes,
        log_output_size=sizes,
        log_rss=rss,
        otel=False,
    )


@pytest.fixture
def _enabled_compactor(monkeypatch) -> None:
    """Swap Tracer's compactor for one with compaction enabled."""
    monkeypatch.setattr(
        tracers.Tracer,
        "compactor",
        Compactor(Thresholds(compact=True, compact_threshold=3)),
    )


@pytest.mark.usefixtures("_enabled_compactor")
def test_tracer_passes_size_and_rss_through_to_compactor(mocker, monkeypatch):
    """Size/rss flags on → compacted summary contains aggregated extras."""
    monkeypatch.setattr(tracers, "resolve_trace_flags", lambda **_: _flags(sizes=True, rss=True))
    monkeypatch.setattr(tracers, "measure_size_mb", lambda _: 0.25)
    monkeypatch.setattr(tracers, "read_rss_mb", lambda: 50.0)
    monkeypatch.setattr(tracers, "read_peak_rss_mb", lambda: 75.0)

    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    def leaf():
        return [0]

    for _ in range(LEAF_REPETITIONS_WITH_EXTRAS):
        tracers.Tracer.trace(leaf, (), {})

    def other():
        return None

    tracers.Tracer.trace(other, (), {})  # different sibling → flush leaf streak

    rendered = [_strip(r) for r in _rendered(mock_logger)]
    memory_line = next(r for r in rendered if "memory:" in r)
    assert "Σin:" in memory_line
    assert "Σout:" in memory_line
    assert "rss:" in memory_line
    assert "peak:" in memory_line


def test_tracer_skips_compaction_when_compact_disabled(mocker, monkeypatch):
    """compact=False → Tracer renders each call via log_span_success."""
    monkeypatch.setattr(tracers.Tracer, "compactor", Compactor(Thresholds(compact=False)))
    monkeypatch.setattr(tracers, "resolve_trace_flags", lambda **_: _flags())
    spy = mocker.patch.object(tracers.profilers, "log_span_success")

    def leaf():
        return None

    for _ in range(LEAF_REPETITIONS_DISABLED):
        tracers.Tracer.trace(leaf, (), {})

    assert spy.call_count == LEAF_REPETITIONS_DISABLED


@pytest.mark.usefixtures("_enabled_compactor")
def test_tracer_compacts_repeated_leaf_to_single_summary(mocker, monkeypatch):
    """compact=True + identical sibling streak → 1 summary, not N entries."""
    monkeypatch.setattr(tracers, "resolve_trace_flags", lambda **_: _flags())
    spy = mocker.patch.object(tracers.profilers, "log_span_success")
    mock_logger = mocker.patch("omniray.tracing.compactor.logger")

    def leaf():
        return None

    for _ in range(LEAF_REPETITIONS_COMPACTED):
        tracers.Tracer.trace(leaf, (), {})

    def other():
        return None

    tracers.Tracer.trace(other, (), {})

    # log_span_success is the per-call legacy renderer — must NOT be invoked
    # for any of the compacted leaves.
    assert spy.call_count == 0
    rendered = [_strip(r) for r in _rendered(mock_logger)]
    summary_lines = [r for r in rendered if "x10" in r and "leaf" in r]
    assert len(summary_lines) == 1
