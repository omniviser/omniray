"""Span profiling and performance visualization."""

import logging
import os
import sys

from colorama import Fore, Style, init

logger = logging.getLogger("omniray.tracing")

# Enable colors controlled by OMNIRAY_LOG_COLOR environment variable (default: true)
_ENABLE_COLORS = os.getenv("OMNIRAY_LOG_COLOR", "true").lower() in ("true", "1", "yes")
init(strip=not _ENABLE_COLORS, autoreset=True)


def _resolve_unicode_support() -> bool:
    """Determine whether to use Unicode box-drawing characters.

    Controlled by ``OMNIRAY_LOG_STYLE`` env var:
    - ``unicode`` — force box-drawing chars
    - ``ascii``   — force ASCII fallback
    - ``auto``    — detect from ``sys.stderr.encoding`` (default)
    """
    style = os.getenv("OMNIRAY_LOG_STYLE", "auto").lower()
    if style == "unicode":
        return True
    if style == "ascii":
        return False
    # auto: detect stderr encoding
    encoding = getattr(sys.stderr, "encoding", "") or ""
    return encoding.lower().replace("-", "") in ("utf8", "utf_8")


_USE_UNICODE = _resolve_unicode_support()


def _read_size_warning_threshold() -> float:
    """Parse ``OMNIRAY_SIZE_WARNING_MB`` (default 10.0).

    Invalid values fall back to the default — tracing must never break startup.
    """
    raw = os.getenv("OMNIRAY_SIZE_WARNING_MB")
    if raw is None:
        return 10.0
    try:
        return float(raw)
    except ValueError:
        return 10.0


_SIZE_WARNING_MB = _read_size_warning_threshold()

# Box-drawing characters (unicode vs ASCII fallback)
TOP_START = "┌─ " if _USE_UNICODE else "+- "
TOP_END = "└─ " if _USE_UNICODE else "\\- "
PIPE = "│  " if _USE_UNICODE else "|  "
NEST_START = "├─ ┌─ " if _USE_UNICODE else "|- +- "
NEST_END = "│  └─ " if _USE_UNICODE else "|  \\- "


class SpanProfiler:
    """Handles span profiling, logging, and performance visualization."""

    _THRESHOLD_FAST = 1
    _THRESHOLD_NORMAL = 10
    _THRESHOLD_SLOW = 100
    _THRESHOLD_WARNING = 200

    @classmethod
    def log_span_success(
        cls,
        span_name: str,
        duration_ms: float,
        current_depth: int,
        *,
        input_size_mb: float | None = None,
        output_size_mb: float | None = None,
    ) -> None:
        """Log span success with colored timing and optional I/O sizes."""
        indent = cls.get_indent(current_depth, is_start=False)
        color = cls._get_color_for_duration(duration_ms)
        reset = Style.RESET_ALL
        slow_warning = cls._get_warning_symbol(duration_ms)
        size_warning = cls._get_size_warning_symbol(input_size_mb, output_size_mb)
        segments = ["%s%s(%.2fms"]
        values: list[object] = [indent, color, duration_ms]
        if input_size_mb is not None:
            segments.append(", in: %.2fMB")
            values.append(input_size_mb)
        if output_size_mb is not None:
            segments.append(", out: %.2fMB")
            values.append(output_size_mb)
        segments.append(")%s %s%s")
        values.extend([reset, span_name, slow_warning + size_warning])
        logger.info("".join(segments), *values)

    @classmethod
    def log_span_failure(cls, span_name: str, duration_ms: float, current_depth: int) -> None:
        """Log span failure with timing (format: indent + timing + name + [FAIL])."""
        indent = cls.get_indent(current_depth, is_start=False)
        logger.info(
            "%s(%.2fms) %s [FAIL]",
            indent,
            duration_ms,
            span_name,
        )

    @staticmethod
    def log_section_separator(depth: int) -> None:
        """Log empty line to separate sections."""
        if depth == 0:
            logger.info("")

    @staticmethod
    def get_indent(depth: int, *, is_start: bool = True) -> str:
        """Get indentation string based on call depth."""
        if depth == 0:
            return TOP_START if is_start else TOP_END
        prefix = PIPE * (depth - 1)
        return prefix + (NEST_START if is_start else NEST_END)

    @classmethod
    def _get_color_for_duration(cls, duration_ms: float) -> str:
        """Get colorama color code based on duration."""
        if duration_ms < cls._THRESHOLD_FAST:
            return Style.DIM
        if duration_ms < cls._THRESHOLD_NORMAL:
            return Fore.GREEN
        if duration_ms < cls._THRESHOLD_SLOW:
            return Fore.YELLOW
        return Fore.RED + Style.BRIGHT

    @classmethod
    def _get_warning_symbol(cls, duration_ms: float) -> str:
        """Get warning symbol for slow operations."""
        return " [SLOW]" if duration_ms >= cls._THRESHOLD_WARNING else ""

    @classmethod
    def _get_size_warning_symbol(
        cls,
        input_size_mb: float | None,
        output_size_mb: float | None,
    ) -> str:
        """Return ``" [BIG]"`` when either size crosses the MB threshold."""
        if input_size_mb is None and output_size_mb is None:
            return ""
        biggest = max(input_size_mb or 0.0, output_size_mb or 0.0)
        return " [BIG]" if biggest >= _SIZE_WARNING_MB else ""
