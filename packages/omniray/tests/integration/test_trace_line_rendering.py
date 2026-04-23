"""End-to-end integration tests for the rendered trace line.

Exercises the real stack: ``@trace()`` → real ``pympler.asizeof`` / ``psutil`` /
``resource.getrusage`` → real ``omniray.tracing`` logger. Lines are captured
via ``omniray_caplog`` fixture and asserted after stripping ANSI.
"""

import re
import time

from colorama import Fore, Style
from omniray.decorators import trace
from omniray.tracing import flags as flags_module
from omniray.tracing import profilers
from omniray.tracing.thresholds import Thresholds


def _enable_flags(monkeypatch, **flag_values: bool) -> None:
    """Set module-level flag constants and clear the resolver cache.

    Flags are resolved once at import; in tests we patch the module-level
    constants directly (the same pattern as ``test_otel_override.py``).
    """
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


def _last_span_line(plain_lines: list[str]) -> str:
    """Return the last non-separator line that contains a closing '└─ ('."""
    for line in reversed(plain_lines):
        if "└─ (" in line or "└─ (" in line:  # span close marker
            return line
    msg = f"no span close line in: {plain_lines!r}"
    raise AssertionError(msg)


def test_duration_only_backward_compat(monkeypatch, omniray_caplog):
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True)
    plain, _ = omniray_caplog

    @trace()
    def noop():
        return None

    noop()

    line = _last_span_line(plain())
    assert "ms)" in line
    assert "MB" not in line
    assert "in:" not in line
    assert "out:" not in line
    assert "rss:" not in line
    assert "[SLOW]" not in line
    assert "[BIG]" not in line


def test_input_output_size_rendered(monkeypatch, omniray_caplog):
    _enable_flags(
        monkeypatch,
        CONSOLE_LOG_FLAG=True,
        LOG_INPUT_SIZE_FLAG=True,
        LOG_OUTPUT_SIZE_FLAG=True,
    )
    plain, _ = omniray_caplog

    @trace()
    def echo(_x):
        return b"y" * (2 * 1024 * 1024)

    echo(b"x" * (1 * 1024 * 1024))

    line = _last_span_line(plain())
    assert "in: " in line
    assert "MB" in line
    assert "out: " in line
    assert "rss:" not in line
    match_out = re.search(r"out:\s*([\d.]+)MB", line)
    assert match_out is not None
    assert float(match_out.group(1)) >= 2.0  # ~2 MB returned


def test_rss_segment_with_delta_and_peak(monkeypatch, omniray_caplog):
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True, LOG_RSS_FLAG=True)
    plain, _ = omniray_caplog

    @trace()
    def allocate():
        return [0.1 * i for i in range(500_000)]

    allocate()

    line = _last_span_line(plain())
    assert "rss: " in line
    assert "\u0394" in line  # Δ segment present
    assert "max: " in line

    match = re.search(r"rss:\s*([\d.]+)MB \(\u0394[+-]?[\d.]+MB, max:\s*([\d.]+)MB\)", line)
    assert match is not None, f"rss segment not parseable in: {line!r}"
    current = float(match.group(1))
    peak = float(match.group(2))
    assert peak >= current, f"peak ({peak}) must be >= current ({current})"


def test_big_tag_appears_on_large_payload(monkeypatch, omniray_caplog):
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True, LOG_OUTPUT_SIZE_FLAG=True)
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=1.0))
    plain, _ = omniray_caplog

    @trace()
    def heavy():
        return b"y" * (5 * 1024 * 1024)

    heavy()

    line = _last_span_line(plain())
    assert line.rstrip().endswith("[BIG]")


def test_slow_tag_and_combined_with_big(monkeypatch, omniray_caplog):
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True, LOG_OUTPUT_SIZE_FLAG=True)
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=1.0))
    plain, _ = omniray_caplog

    @trace()
    def slow_and_heavy():
        time.sleep(0.3)  # > 200 ms SLOW threshold, with margin for slow CI
        return b"y" * (5 * 1024 * 1024)

    slow_and_heavy()

    line = _last_span_line(plain())
    assert line.rstrip().endswith("[SLOW] [BIG]")


def test_custom_thresholds_override_colors(monkeypatch, omniray_caplog):
    """Custom lower thresholds promote a small value to the RED color class."""
    custom = Thresholds(
        size_mb=(0.001, 0.005, 0.01),
        rss_mb=(100.0, 500.0, 1000.0),
        rss_delta_mb=(1.0, 10.0, 100.0),
        duration_ms=(1.0, 10.0, 100.0),
        duration_slow_tag_ms=200.0,
    )
    monkeypatch.setattr(profilers, "_THRESHOLDS", custom)
    _enable_flags(monkeypatch, CONSOLE_LOG_FLAG=True, LOG_OUTPUT_SIZE_FLAG=True)
    _, raw = omniray_caplog

    @trace()
    def small():
        return b"y" * (50 * 1024)  # ~0.05 MB — above hi=0.01 → RED

    small()

    red = Fore.RED + Style.BRIGHT
    raw_lines = raw()
    assert any(red in line for line in raw_lines), (
        f"expected RED color code in output; got: {raw_lines!r}"
    )
