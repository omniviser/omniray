"""Span profiling and performance visualization."""

import logging
import os
import sys

from colorama import Fore, Style, init

from omniray.tracing.thresholds import Thresholds

logger = logging.getLogger("omniray.tracing")

_THRESHOLDS = Thresholds.from_pyproject()

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
DELTA = "Δ" if _USE_UNICODE else "d"


def log_span_success(  # noqa: PLR0913
    span_name: str,
    duration_ms: float,
    current_depth: int,
    *,
    input_size_mb: float | None = None,
    output_size_mb: float | None = None,
    rss_current_mb: float | None = None,
    rss_delta_mb: float | None = None,
    rss_peak_mb: float | None = None,
) -> None:
    """Log span success with per-segment colored values."""
    body = _colored(
        _bucket_color(duration_ms, _THRESHOLDS.duration_ms),
        f"{duration_ms:.2f}ms",
    )
    if input_size_mb is not None:
        body += ", in: " + _format_mb(input_size_mb, _THRESHOLDS.size_mb)
    if output_size_mb is not None:
        body += ", out: " + _format_mb(output_size_mb, _THRESHOLDS.size_mb)
    if rss_current_mb is not None:
        body += ", rss: " + _format_mb(rss_current_mb, _THRESHOLDS.rss_mb)
        extras = _format_rss_extras(rss_delta_mb, rss_peak_mb)
        if extras:
            body += f" ({extras})"

    indent = get_indent(current_depth, is_start=False)
    tags = _get_warning_symbol(duration_ms) + _get_size_warning_symbol(
        input_size_mb, output_size_mb
    )
    logger.info("%s(%s) %s%s", indent, body, span_name, tags)


def log_span_failure(span_name: str, duration_ms: float, current_depth: int) -> None:
    """Log span failure with timing (format: indent + timing + name + [FAIL])."""
    indent = get_indent(current_depth, is_start=False)
    logger.info(
        "%s(%.2fms) %s [FAIL]",
        indent,
        duration_ms,
        span_name,
    )


def log_section_separator(depth: int) -> None:
    """Log empty line to separate sections."""
    if depth == 0:
        logger.info("")


def get_indent(depth: int, *, is_start: bool = True) -> str:
    """Get indentation string based on call depth."""
    if depth == 0:
        return TOP_START if is_start else TOP_END
    prefix = PIPE * (depth - 1)
    return prefix + (NEST_START if is_start else NEST_END)


def _colored(color: str, text: str) -> str:
    """Wrap *text* in *color* with a trailing style reset."""
    return f"{color}{text}{Style.RESET_ALL}"


def _bucket_color(value: float, thresholds: tuple[float, float, float]) -> str:
    """Map *value* onto a DIM/GREEN/YELLOW/RED bucket using ``(low, medium, high)``."""
    low, medium, high = thresholds
    if value < low:
        return Style.DIM
    if value < medium:
        return Fore.GREEN
    if value < high:
        return Fore.YELLOW
    return Fore.RED + Style.BRIGHT


def _format_mb(value: float, thresholds: tuple[float, float, float], *, sign: bool = False) -> str:
    """Return a colored ``X.XXMB`` string; ``sign=True`` forces a leading +/-."""
    spec = f"{value:+.2f}" if sign else f"{value:.2f}"
    return _colored(_bucket_color(value, thresholds), f"{spec}MB")


def _format_rss_extras(rss_delta_mb: float | None, rss_peak_mb: float | None) -> str:
    """Build the ``Δ..., max: ...`` group (empty string when both inputs are ``None``)."""
    extras: list[str] = []
    if rss_delta_mb is not None:
        extras.append(DELTA + _format_mb(rss_delta_mb, _THRESHOLDS.rss_delta_mb, sign=True))
    if rss_peak_mb is not None:
        extras.append("max: " + _format_mb(rss_peak_mb, _THRESHOLDS.rss_mb))
    return ", ".join(extras)


def _get_warning_symbol(duration_ms: float) -> str:
    """Get warning symbol for slow operations."""
    return " [SLOW]" if duration_ms >= _THRESHOLDS.duration_slow_tag_ms else ""


def _get_size_warning_symbol(
    input_size_mb: float | None,
    output_size_mb: float | None,
) -> str:
    """Return ``" [BIG]"`` when either size crosses the MB threshold."""
    if input_size_mb is None and output_size_mb is None:
        return ""
    biggest = max(input_size_mb or 0.0, output_size_mb or 0.0)
    return " [BIG]" if biggest >= _THRESHOLDS.size_big_tag_mb else ""
