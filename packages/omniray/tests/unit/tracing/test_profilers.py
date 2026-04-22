"""Tests for span profiler module."""

import pytest
from colorama import Fore, Style
from omniray.tracing import profilers
from omniray.tracing.profilers import SpanProfiler


def test_log_span_success(mocker):
    """Test log_span_success logs correct format with colors."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    duration_ms = 5.5
    SpanProfiler.log_span_success("test_span", duration_ms, 0)

    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args[0]
    assert "test_span" in call_args[-2]
    assert call_args[3] == duration_ms  # duration_ms passed to format string


def test_log_span_success_no_sizes_unchanged_format(mocker):
    """Backward-compat: no size kwargs → format contains (%.2fms) only, no 'MB'."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0)

    mock_logger.info.assert_called_once()
    fmt = mock_logger.info.call_args[0][0]
    assert "(%.2fms)" in fmt
    assert "MB" not in fmt


def test_log_span_success_with_input_size_only(mocker):
    """input_size_mb set, output_size_mb None → only 'in: %.2fMB' in format."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, input_size_mb=0.5)

    mock_logger.info.assert_called_once()
    fmt = mock_logger.info.call_args[0][0]
    assert "in: %.2fMB" in fmt
    assert "out:" not in fmt
    assert 0.5 in mock_logger.info.call_args[0]


def test_log_span_success_with_output_size_only(mocker):
    """output_size_mb set, input_size_mb None → only 'out: %.2fMB' in format."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, output_size_mb=1.2)

    mock_logger.info.assert_called_once()
    fmt = mock_logger.info.call_args[0][0]
    assert "out: %.2fMB" in fmt
    assert "in:" not in fmt
    assert 1.2 in mock_logger.info.call_args[0]


def test_log_span_success_with_both_sizes(mocker):
    """Both sizes → 'in: %.2fMB' comes before 'out: %.2fMB'."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, input_size_mb=0.5, output_size_mb=1.2)

    fmt = mock_logger.info.call_args[0][0]
    assert fmt.index("in: %.2fMB") < fmt.index("out: %.2fMB")
    assert 0.5 in mock_logger.info.call_args[0]
    assert 1.2 in mock_logger.info.call_args[0]


def test_log_span_success_zero_size_renders(mocker):
    """output_size_mb=0.0 still renders segment (distinguishes from None)."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, output_size_mb=0.0)

    fmt = mock_logger.info.call_args[0][0]
    assert "out: %.2fMB" in fmt


def test_log_span_success_big_tag_appears_when_output_exceeds(mocker, monkeypatch):
    """output size over threshold → final positional arg contains ' [BIG]'."""
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 1.0)
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, output_size_mb=2.0)

    trailing = mock_logger.info.call_args[0][-1]
    assert " [BIG]" in trailing
    assert "[SLOW]" not in trailing


def test_log_span_success_both_slow_and_big_tags(mocker, monkeypatch):
    """Duration >= 200ms AND size >= threshold → trailing has ' [SLOW] [BIG]'."""
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 10.0)
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 500.0, 0, output_size_mb=50.0)

    trailing = mock_logger.info.call_args[0][-1]
    assert trailing == " [SLOW] [BIG]"


def test_log_span_success_no_big_tag_when_sizes_none(mocker, monkeypatch):
    """No size kwargs → no [BIG] (backward-compat preserved regardless of threshold)."""
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 0.0001)
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0)

    trailing = mock_logger.info.call_args[0][-1]
    assert "[BIG]" not in trailing


# --- RSS segment ---


def test_log_span_success_rss_current_only(mocker):
    """rss_current_mb alone → 'rss: X.XXMB' without delta segment."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, rss_current_mb=234.5)

    fmt = mock_logger.info.call_args[0][0]
    assert ", rss: %.2fMB" in fmt
    assert "\u0394" not in fmt


def test_log_span_success_rss_current_and_delta_positive(mocker):
    """Both rss values → 'rss: X.XXMB (\u0394+Y.YYMB)' with both in call args."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success(
        "test_span", 5.5, 0, rss_current_mb=234.5, rss_delta_mb=12.34
    )

    call_args = mock_logger.info.call_args[0]
    fmt = call_args[0]
    assert ", rss: %.2fMB" in fmt
    assert "(\u0394%+.2fMB)" in fmt
    assert 234.5 in call_args
    assert 12.34 in call_args


def test_log_span_success_rss_negative_delta_value_is_negative(mocker):
    """Negative delta passes as negative float; %+ handles sign rendering."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success(
        "test_span", 5.5, 0, rss_current_mb=100.0, rss_delta_mb=-5.0
    )

    assert -5.0 in mock_logger.info.call_args[0]


def test_log_span_success_rss_both_none_no_segment(mocker):
    """rss both None → no 'rss:' in format (backward-compat)."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0)

    fmt = mock_logger.info.call_args[0][0]
    assert "rss:" not in fmt


def test_log_span_success_segment_order_in_then_out_then_rss(mocker):
    """With all segments: 'in:' before 'out:' before 'rss:' in format string."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success(
        "test_span",
        5.5,
        0,
        input_size_mb=0.1,
        output_size_mb=1.2,
        rss_current_mb=234.5,
        rss_delta_mb=12.34,
    )

    fmt = mock_logger.info.call_args[0][0]
    assert fmt.index("in: %.2fMB") < fmt.index("out: %.2fMB") < fmt.index("rss: %.2fMB")


def test_log_span_success_rss_peak_only(mocker):
    """rss_current + rss_peak (no delta) → '(max: %.2fMB)' without Δ."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success(
        "test_span", 5.5, 0, rss_current_mb=100.0, rss_peak_mb=3000.0
    )

    call_args = mock_logger.info.call_args[0]
    fmt = call_args[0]
    assert "(max: %.2fMB)" in fmt
    assert "\u0394" not in fmt
    assert 3000.0 in call_args


def test_log_span_success_rss_delta_and_peak_both(mocker):
    """Both delta and peak → '(Δ%+.2fMB, max: %.2fMB)' — delta first, peak second."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success(
        "test_span",
        5.5,
        0,
        rss_current_mb=234.5,
        rss_delta_mb=12.34,
        rss_peak_mb=3000.0,
    )

    call_args = mock_logger.info.call_args[0]
    fmt = call_args[0]
    assert "(\u0394%+.2fMB, max: %.2fMB)" in fmt
    assert 234.5 in call_args
    assert 12.34 in call_args
    assert 3000.0 in call_args


def test_log_span_success_rss_peak_alone_when_current_none(mocker):
    """rss_peak given but rss_current None → no 'rss:' segment at all (peak gated)."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_success("test_span", 5.5, 0, rss_peak_mb=3000.0)

    fmt = mock_logger.info.call_args[0][0]
    assert "rss:" not in fmt
    assert "max:" not in fmt


def test_log_span_failure(mocker):
    """Test log_span_failure logs correct format."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_span_failure("test_span", 10.0, 0)

    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args[0]
    assert "[FAIL]" in call_args[0]


def test_log_section_separator_depth_zero(mocker):
    """Test log_section_separator logs empty line at depth 0."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_section_separator(0)

    mock_logger.info.assert_called_once_with("")


def test_log_section_separator_depth_nonzero(mocker):
    """Test log_section_separator does nothing at depth > 0."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    SpanProfiler.log_section_separator(1)

    mock_logger.info.assert_not_called()


def test_get_indent_depth_zero_start():
    """Test get_indent returns start symbol at depth 0."""
    result = SpanProfiler.get_indent(0, is_start=True)

    assert result == "┌─ "


def test_get_indent_depth_zero_end():
    """Test get_indent returns end symbol at depth 0."""
    result = SpanProfiler.get_indent(0, is_start=False)

    assert result == "└─ "


def test_get_indent_depth_one_start():
    """Test get_indent returns correct indent at depth 1 start."""
    result = SpanProfiler.get_indent(1, is_start=True)

    assert result == "├─ ┌─ "


def test_get_indent_depth_one_end():
    """Test get_indent returns correct indent at depth 1 end."""
    result = SpanProfiler.get_indent(1, is_start=False)

    assert result == "│  └─ "


def test_get_indent_depth_two():
    """Test get_indent returns correct indent at depth 2."""
    result = SpanProfiler.get_indent(2, is_start=True)

    assert result == "│  ├─ ┌─ "


@pytest.mark.parametrize(
    ("duration_ms", "expected_color"),
    [
        (0.5, Style.DIM),  # < 1ms - fast
        (5.0, Fore.GREEN),  # < 10ms - normal
        (50.0, Fore.YELLOW),  # < 100ms - slow
        (150.0, Fore.RED + Style.BRIGHT),  # >= 100ms - very slow
    ],
)
def test_get_color_for_duration(duration_ms, expected_color):
    """Test _get_color_for_duration returns correct color for different durations."""
    result = SpanProfiler._get_color_for_duration(duration_ms)

    assert result == expected_color


def test_get_warning_symbol_slow():
    """Test _get_warning_symbol returns [SLOW] for duration >= 200ms."""
    result = SpanProfiler._get_warning_symbol(200.0)

    assert result == " [SLOW]"


def test_get_warning_symbol_normal():
    """Test _get_warning_symbol returns empty string for duration < 200ms."""
    result = SpanProfiler._get_warning_symbol(199.0)

    assert result == ""


# --- _get_size_warning_symbol / _read_size_warning_threshold ---


def test_get_size_warning_symbol_both_none_returns_empty():
    assert SpanProfiler._get_size_warning_symbol(None, None) == ""


def test_get_size_warning_symbol_below_threshold_returns_empty(monkeypatch):
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 10.0)
    assert SpanProfiler._get_size_warning_symbol(5.0, 8.0) == ""


def test_get_size_warning_symbol_input_above_threshold(monkeypatch):
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 10.0)
    assert SpanProfiler._get_size_warning_symbol(15.0, 1.0) == " [BIG]"


def test_get_size_warning_symbol_output_above_threshold(monkeypatch):
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 10.0)
    assert SpanProfiler._get_size_warning_symbol(1.0, 20.0) == " [BIG]"


def test_get_size_warning_symbol_threshold_boundary(monkeypatch):
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 10.0)
    assert SpanProfiler._get_size_warning_symbol(10.0, None) == " [BIG]"


def test_get_size_warning_symbol_none_and_small(monkeypatch):
    monkeypatch.setattr(profilers, "_SIZE_WARNING_MB", 10.0)
    assert SpanProfiler._get_size_warning_symbol(None, 0.5) == ""


def test_read_size_warning_threshold_default(monkeypatch):
    monkeypatch.delenv("OMNIRAY_SIZE_WARNING_MB", raising=False)
    assert profilers._read_size_warning_threshold() == 10.0


def test_read_size_warning_threshold_custom(monkeypatch):
    monkeypatch.setenv("OMNIRAY_SIZE_WARNING_MB", "5")
    assert profilers._read_size_warning_threshold() == 5.0


def test_read_size_warning_threshold_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("OMNIRAY_SIZE_WARNING_MB", "abc")
    assert profilers._read_size_warning_threshold() == 10.0


# --- ASCII fallback tests ---


def test_get_indent_ascii_fallback(monkeypatch):
    """Test get_indent produces ASCII output when constants are patched."""
    monkeypatch.setattr(profilers, "TOP_START", "+- ")
    monkeypatch.setattr(profilers, "TOP_END", "\\- ")
    monkeypatch.setattr(profilers, "PIPE", "|  ")
    monkeypatch.setattr(profilers, "NEST_START", "|- +- ")
    monkeypatch.setattr(profilers, "NEST_END", "|  \\- ")

    assert SpanProfiler.get_indent(0, is_start=True) == "+- "
    assert SpanProfiler.get_indent(0, is_start=False) == "\\- "
    assert SpanProfiler.get_indent(1, is_start=True) == "|- +- "
    assert SpanProfiler.get_indent(1, is_start=False) == "|  \\- "
    assert SpanProfiler.get_indent(2, is_start=True) == "|  |- +- "


# --- _resolve_unicode_support tests ---


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [
        ("utf-8", True),
        ("UTF-8", True),
        ("utf_8", True),
        ("ascii", False),
        ("latin-1", False),
        ("", False),
    ],
)
def test_resolve_unicode_support_auto_detection(monkeypatch, encoding, expected):
    """Test _resolve_unicode_support auto-detects from stderr encoding."""
    monkeypatch.delenv("OMNIRAY_LOG_STYLE", raising=False)
    monkeypatch.setattr("sys.stderr", type("FakeStderr", (), {"encoding": encoding})())

    assert profilers._resolve_unicode_support() is expected


def test_resolve_unicode_support_missing_encoding(monkeypatch):
    """Test _resolve_unicode_support handles stderr without encoding attr."""
    monkeypatch.delenv("OMNIRAY_LOG_STYLE", raising=False)
    monkeypatch.setattr("sys.stderr", object())

    assert profilers._resolve_unicode_support() is False


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("unicode", True),
        ("ascii", False),
    ],
)
def test_resolve_unicode_support_forced_style(monkeypatch, style, expected):
    """Test OMNIRAY_LOG_STYLE overrides auto-detection."""
    monkeypatch.setenv("OMNIRAY_LOG_STYLE", style)

    assert profilers._resolve_unicode_support() is expected
