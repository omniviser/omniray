"""Collapse repeated leaf-call siblings into a single summary line.

Hot loops calling the same helper N times (e.g. 28x ``AzureFunc.post``)
collapse to one ``xN`` summary instead of flooding the trace with N
identical start/end pairs. Configured via ``[tool.omniray]`` keys
``compact`` and ``compact_threshold`` in ``pyproject.toml``.

See: https://omniviser.github.io/omniray/guide/configuration/#streak-compaction
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from colorama import Fore, Style

from omniray.tracing import profilers
from omniray.tracing.console import logger

if TYPE_CHECKING:
    from omniray.tracing.thresholds import Thresholds


@dataclass
class _Pending:
    """A call whose start line has been deferred until we know its fate."""

    span_name: str
    depth: int
    has_children: bool = False


@dataclass
class _Streak:
    """Running aggregate for repeated leaf calls at one depth."""

    span_name: str
    depth: int
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    total_input_mb: float | None = None
    total_output_mb: float | None = None
    max_rss_mb: float | None = None
    total_rss_delta_mb: float | None = None
    max_rss_peak_mb: float | None = None

    def add(  # noqa: PLR0913
        self,
        duration_ms: float,
        *,
        input_size_mb: float | None = None,
        output_size_mb: float | None = None,
        rss_current_mb: float | None = None,
        rss_delta_mb: float | None = None,
        rss_peak_mb: float | None = None,
    ) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
        self.total_input_mb = self._sum(self.total_input_mb, input_size_mb)
        self.total_output_mb = self._sum(self.total_output_mb, output_size_mb)
        self.max_rss_mb = self._max(self.max_rss_mb, rss_current_mb)
        self.total_rss_delta_mb = self._sum(self.total_rss_delta_mb, rss_delta_mb)
        self.max_rss_peak_mb = self._max(self.max_rss_peak_mb, rss_peak_mb)

    @staticmethod
    def _sum(running: float | None, value: float | None) -> float | None:
        """Sum two optionals: None+None=None, mixed=value, both=sum."""
        if value is None:
            return running
        return value if running is None else running + value

    @staticmethod
    def _max(running: float | None, value: float | None) -> float | None:
        """Max of two optionals: None+None=None, mixed=value, both=max."""
        if value is None:
            return running
        return value if running is None else max(running, value)


@dataclass
class _State:
    """Per-call-tree mutable state — one instance lives in each ContextVar context."""

    pending_stack: list[_Pending] = field(default_factory=list)
    streaks: dict[int, _Streak] = field(default_factory=dict)


class Compactor:
    """Tree-aware leaf-call streak collapser.

    Each instance owns its own ``ContextVar`` so tests can swap in a fresh
    Compactor without state leaking between cases. The Tracer holds one
    instance configured from ``pyproject.toml`` at import.
    """

    def __init__(self, thresholds: Thresholds) -> None:
        self._thresholds = thresholds
        # Per-instance ContextVar — id() in the name keeps it unique even
        # when multiple Compactors live in the same process.
        self._state: ContextVar[_State | None] = ContextVar(
            f"omniray_compactor_state_{id(self)}", default=None
        )

    @property
    def enabled(self) -> bool:
        """Whether this compactor will absorb leaf streaks (config-driven)."""
        return self._thresholds.compact

    @property
    def threshold(self) -> int:
        """Minimum streak count required to emit a summary instead of per-call."""
        return self._thresholds.compact_threshold

    def _get_state(self) -> _State:
        state = self._state.get()
        if state is None:
            state = _State()
            self._state.set(state)
        return state

    def note_entry(self, span_name: str, depth: int) -> bool:
        """Buffer this call's start. Returns True iff start line should be deferred.

        If a parent on the stack hasn't logged its own start yet (leaf-candidate),
        the new child entry promotes the parent to non-leaf — we log the parent's
        start line retroactively and any leaf streak at the parent's depth is
        flushed (siblings interrupted).
        """
        if not self.enabled:
            return False
        state = self._get_state()
        if state.pending_stack:
            parent = state.pending_stack[-1]
            if not parent.has_children:
                parent.has_children = True
                self._flush_streak(state, parent.depth)
                logger.info(
                    "%s%s",
                    profilers.get_indent(parent.depth, is_start=True),
                    parent.span_name,
                )
        streak = state.streaks.get(depth)
        if streak is not None and streak.span_name != span_name:
            self._flush_streak(state, depth)
        state.pending_stack.append(_Pending(span_name=span_name, depth=depth))
        return True

    def note_exit_success(  # noqa: PLR0913
        self,
        span_name: str,
        depth: int,
        duration_ms: float,
        *,
        input_size_mb: float | None = None,
        output_size_mb: float | None = None,
        rss_current_mb: float | None = None,
        rss_delta_mb: float | None = None,
        rss_peak_mb: float | None = None,
    ) -> bool:
        """Absorb a successful leaf exit into the streak buffer.

        Returns True iff the call was compacted into the streak buffer
        (caller must not log normally — summary will render at flush time).
        Returns False for non-leaves so the caller renders them per-call.
        """
        if not self.enabled:
            return False
        state = self._get_state()
        if not state.pending_stack:
            return False
        pending = state.pending_stack.pop()
        if pending.has_children:
            self._flush_streak(state, depth + 1)
            return False
        streak = state.streaks.get(depth)
        if streak is not None and streak.span_name != span_name:
            self._flush_streak(state, depth)
            streak = None
        if streak is None:
            streak = _Streak(span_name=span_name, depth=depth)
            state.streaks[depth] = streak
        streak.add(
            duration_ms,
            input_size_mb=input_size_mb,
            output_size_mb=output_size_mb,
            rss_current_mb=rss_current_mb,
            rss_delta_mb=rss_delta_mb,
            rss_peak_mb=rss_peak_mb,
        )
        return True

    def note_exit_failure(self, depth: int) -> None:
        """Flush streaks before an error is logged so the failure isn't masked."""
        if not self.enabled:
            return
        state = self._get_state()
        if state.pending_stack and state.pending_stack[-1].depth == depth:
            state.pending_stack.pop()
        self._flush_streak(state, depth)
        self._flush_streak(state, depth + 1)

    def _flush_streak(self, state: _State, depth: int) -> None:
        streak = state.streaks.pop(depth, None)
        if streak is None:
            return
        if streak.count >= self.threshold:
            self._emit_summary(streak)
        else:
            self._emit_each(streak)

    def _emit_summary(self, streak: _Streak) -> None:
        avg_ms = streak.total_ms / streak.count
        logger.info(
            "%s%s",
            profilers.get_indent(streak.depth, is_start=True),
            streak.span_name,
        )
        logger.info(
            "%s%s %s",
            profilers.get_indent(streak.depth, is_start=False),
            profilers._colored(Fore.RED + Style.BRIGHT, f"x{streak.count}"),  # noqa: SLF001
            streak.span_name,
        )
        cont = _continuation_indent(streak.depth)
        logger.info("%stime: %s", cont, _format_time_line(streak, avg_ms, self._thresholds))
        memory = _format_memory_line(streak, self._thresholds)
        if memory:
            logger.info("%smemory: %s", cont, memory)

    def _emit_each(self, streak: _Streak) -> None:
        """Render below-threshold streak as individual start/end pairs.

        Per-call durations aren't kept once a streak forms (only sum/min/max
        are tracked) so each line uses the average — exact timings are lost,
        but sum and span name remain accurate.
        """
        avg_ms = streak.total_ms / streak.count
        start_indent = profilers.get_indent(streak.depth, is_start=True)
        end_indent = profilers.get_indent(streak.depth, is_start=False)
        for _ in range(streak.count):
            logger.info("%s%s", start_indent, streak.span_name)
            logger.info("%s(%.2fms) %s", end_indent, avg_ms, streak.span_name)


def _continuation_indent(depth: int) -> str:
    r"""Indent for continuation lines hanging under the leaf marker.

    Preserves ancestor ``│`` pipes so the tree shape stays intact, then
    blanks out the width of the leaf marker (3 chars: ``└─ `` or ``\- ``).
    """
    return profilers.PIPE * depth + "   "


def _format_time_line(streak: _Streak, avg_ms: float, thresholds: Thresholds) -> str:
    """Color each duration field by the configured duration_ms thresholds."""
    parts = [
        "Σ" + _color_ms(streak.total_ms, thresholds),
        "μ" + _color_ms(avg_ms, thresholds),
        "max " + _color_ms(streak.max_ms, thresholds),
    ]
    return ", ".join(parts)


def _color_ms(value_ms: float, thresholds: Thresholds) -> str:
    color = profilers._bucket_color(value_ms, thresholds.duration_ms)  # noqa: SLF001
    return profilers._colored(color, f"{value_ms:.2f}ms")  # noqa: SLF001


def _format_memory_line(streak: _Streak, thresholds: Thresholds) -> str:
    """Build the ``memory:`` continuation line, omitting unset fields."""
    parts: list[str] = []
    if streak.total_input_mb is not None:
        parts.append("Σin: " + profilers._format_mb(streak.total_input_mb, thresholds.size_mb))  # noqa: SLF001
    if streak.total_output_mb is not None:
        parts.append("Σout: " + profilers._format_mb(streak.total_output_mb, thresholds.size_mb))  # noqa: SLF001
    if streak.max_rss_mb is not None:
        parts.append("rss: " + profilers._format_mb(streak.max_rss_mb, thresholds.rss_mb))  # noqa: SLF001
    if streak.total_rss_delta_mb is not None:
        parts.append(
            "Σ"
            + profilers._format_mb(  # noqa: SLF001
                streak.total_rss_delta_mb, thresholds.rss_delta_mb, sign=True
            )
        )
    if streak.max_rss_peak_mb is not None:
        parts.append("peak: " + profilers._format_mb(streak.max_rss_peak_mb, thresholds.rss_mb))  # noqa: SLF001
    return ", ".join(parts)
