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
    def log_span_success(cls, span_name: str, duration_ms: float, current_depth: int) -> None:
        """Log span success with colored timing (format: indent + timing + name + warning)."""
        indent = cls.get_indent(current_depth, is_start=False)
        color = cls._get_color_for_duration(duration_ms)
        reset = Style.RESET_ALL
        warning = cls._get_warning_symbol(duration_ms)
        logger.info(
            "%s%s(%.2fms)%s %s%s",
            indent,
            color,
            duration_ms,
            reset,
            span_name,
            warning,
        )

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
