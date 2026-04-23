"""Tests for span profiler module."""

import pytest
from colorama import Fore, Style
from omniray.tracing import profilers
from omniray.tracing.thresholds import Thresholds


def _rendered(mock_logger) -> str:
    """Apply %-formatting of the last logger.info call and return the final string."""
    call = mock_logger.info.call_args[0]
    return call[0] % call[1:]


def test_log_span_success(mocker):
    """Test log_span_success renders span name and duration."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0)

    mock_logger.info.assert_called_once()
    rendered = _rendered(mock_logger)
    assert "test_span" in rendered
    assert "5.50ms" in rendered


def test_log_span_success_no_sizes_unchanged_format(mocker):
    """Backward-compat: no size kwargs → no 'MB' in rendered output."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0)

    rendered = _rendered(mock_logger)
    assert "5.50ms" in rendered
    assert "MB" not in rendered


def test_log_span_success_with_input_size_only(mocker):
    """input_size_mb set, output_size_mb None → only 'in:' in rendered output."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, input_size_mb=0.5)

    rendered = _rendered(mock_logger)
    assert "in: " in rendered
    assert "0.50MB" in rendered
    assert "out:" not in rendered


def test_log_span_success_with_output_size_only(mocker):
    """output_size_mb set, input_size_mb None → only 'out:' in rendered output."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, output_size_mb=1.2)

    rendered = _rendered(mock_logger)
    assert "out: " in rendered
    assert "1.20MB" in rendered
    assert "in:" not in rendered


def test_log_span_success_with_both_sizes(mocker):
    """Both sizes → 'in:' comes before 'out:' in rendered output."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, input_size_mb=0.5, output_size_mb=1.2)

    rendered = _rendered(mock_logger)
    assert rendered.index("in: ") < rendered.index("out: ")
    assert "0.50MB" in rendered
    assert "1.20MB" in rendered


def test_log_span_success_zero_size_renders(mocker):
    """output_size_mb=0.0 still renders 'out: 0.00MB' (distinguishes from None)."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, output_size_mb=0.0)

    rendered = _rendered(mock_logger)
    assert "out: " in rendered
    assert "0.00MB" in rendered


def test_log_span_success_big_tag_appears_when_output_exceeds(mocker, monkeypatch):
    """output size over threshold → final positional arg contains ' [BIG]'."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=1.0))
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, output_size_mb=2.0)

    trailing = mock_logger.info.call_args[0][-1]
    assert " [BIG]" in trailing
    assert "[SLOW]" not in trailing


def test_log_span_success_both_slow_and_big_tags(mocker, monkeypatch):
    """Duration >= 200ms AND size >= threshold → trailing has ' [SLOW] [BIG]'."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=10.0))
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 500.0, 0, output_size_mb=50.0)

    trailing = mock_logger.info.call_args[0][-1]
    assert trailing == " [SLOW] [BIG]"


def test_log_span_success_no_big_tag_when_sizes_none(mocker, monkeypatch):
    """No size kwargs → no [BIG] (backward-compat preserved regardless of threshold)."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=0.0001))
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0)

    trailing = mock_logger.info.call_args[0][-1]
    assert "[BIG]" not in trailing


def test_log_span_success_rss_current_only(mocker):
    """rss_current_mb alone → 'rss: X.XXMB' without delta segment."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, rss_current_mb=234.5)

    rendered = _rendered(mock_logger)
    assert "rss: " in rendered
    assert "234.50MB" in rendered
    assert "\u0394" not in rendered


def test_log_span_success_rss_current_and_delta_positive(mocker, strip_ansi):
    """Both rss values → 'rss: X.XXMB (ΔY.YYMB)' rendered."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, rss_current_mb=234.5, rss_delta_mb=12.34)

    plain = strip_ansi(_rendered(mock_logger))
    assert "rss: 234.50MB" in plain
    assert "\u0394+12.34MB" in plain


def test_log_span_success_rss_negative_delta_renders_minus(mocker, strip_ansi):
    """Negative delta renders 'Δ-X.XXMB'."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, rss_current_mb=100.0, rss_delta_mb=-5.0)

    plain = strip_ansi(_rendered(mock_logger))
    assert "\u0394-5.00MB" in plain


def test_log_span_success_rss_both_none_no_segment(mocker):
    """rss both None → no 'rss:' rendered (backward-compat)."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0)

    rendered = _rendered(mock_logger)
    assert "rss:" not in rendered


def test_log_span_success_segment_order_in_then_out_then_rss(mocker):
    """With all segments: 'in:' before 'out:' before 'rss:' in rendered output."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success(
        "test_span",
        5.5,
        0,
        input_size_mb=0.1,
        output_size_mb=1.2,
        rss_current_mb=234.5,
        rss_delta_mb=12.34,
    )

    rendered = _rendered(mock_logger)
    assert rendered.index("in: ") < rendered.index("out: ") < rendered.index("rss: ")


def test_log_span_success_rss_peak_only(mocker):
    """rss_current + rss_peak (no delta) → '(max: X.XXMB)' without Δ."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, rss_current_mb=100.0, rss_peak_mb=3000.0)

    rendered = _rendered(mock_logger)
    assert "max: " in rendered
    assert "3000.00MB" in rendered
    assert "\u0394" not in rendered


def test_log_span_success_rss_delta_and_peak_both(mocker, strip_ansi):
    """Both delta and peak → 'Δ' before 'max:' in rendered output."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success(
        "test_span",
        5.5,
        0,
        rss_current_mb=234.5,
        rss_delta_mb=12.34,
        rss_peak_mb=3000.0,
    )

    plain = strip_ansi(_rendered(mock_logger))
    assert plain.index("\u0394+12.34MB") < plain.index("max: ")
    assert "3000.00MB" in plain


def test_log_span_success_rss_peak_alone_when_current_none(mocker):
    """rss_peak given but rss_current None → no 'rss:' segment at all (peak gated)."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.5, 0, rss_peak_mb=3000.0)

    rendered = _rendered(mock_logger)
    assert "rss:" not in rendered
    assert "max:" not in rendered


def test_log_span_success_duration_colored_independently(mocker, monkeypatch):
    """Small duration in GREEN, big size in RED — different ANSI codes in output."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", _DEFAULT_THRESHOLDS)
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.0, 0, output_size_mb=50.0)

    rendered = _rendered(mock_logger)
    # Duration 5ms → GREEN; size 50MB → RED+BRIGHT. Both escape codes must appear.
    assert Fore.GREEN in rendered
    assert (Fore.RED + Style.BRIGHT) in rendered


def test_log_span_success_delta_negative_rendered_dim(mocker, monkeypatch):
    """Negative delta falls into the ``< lo`` bucket → Style.DIM in rendered output."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", _DEFAULT_THRESHOLDS)
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_success("test_span", 5.0, 0, rss_current_mb=100.0, rss_delta_mb=-5.0)

    rendered = _rendered(mock_logger)
    # Find the delta segment and check the color code preceding its value.
    idx = rendered.index("\u0394")
    segment = rendered[idx : idx + 40]
    assert Style.DIM in segment
    assert Fore.GREEN not in segment


def test_log_span_failure(mocker):
    """Test log_span_failure logs correct format."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_span_failure("test_span", 10.0, 0)

    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args[0]
    assert "[FAIL]" in call_args[0]


def test_log_section_separator_depth_zero(mocker):
    """Test log_section_separator logs empty line at depth 0."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_section_separator(0)

    mock_logger.info.assert_called_once_with("")


def test_log_section_separator_depth_nonzero(mocker):
    """Test log_section_separator does nothing at depth > 0."""
    mock_logger = mocker.patch("omniray.tracing.profilers.logger")

    profilers.log_section_separator(1)

    mock_logger.info.assert_not_called()


def test_get_indent_depth_zero_start():
    """Test get_indent returns start symbol at depth 0."""
    result = profilers.get_indent(0, is_start=True)

    assert result == "┌─ "


def test_get_indent_depth_zero_end():
    """Test get_indent returns end symbol at depth 0."""
    result = profilers.get_indent(0, is_start=False)

    assert result == "└─ "


def test_get_indent_depth_one_start():
    """Test get_indent returns correct indent at depth 1 start."""
    result = profilers.get_indent(1, is_start=True)

    assert result == "├─ ┌─ "


def test_get_indent_depth_one_end():
    """Test get_indent returns correct indent at depth 1 end."""
    result = profilers.get_indent(1, is_start=False)

    assert result == "│  └─ "


def test_get_indent_depth_two():
    """Test get_indent returns correct indent at depth 2."""
    result = profilers.get_indent(2, is_start=True)

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
def test_bucket_color_for_duration(monkeypatch, duration_ms, expected_color):
    """Test _bucket_color returns correct color for different durations."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds())
    result = profilers._bucket_color(duration_ms, profilers._THRESHOLDS.duration_ms)

    assert result == expected_color


def test_get_warning_symbol_slow():
    """Test _get_warning_symbol returns [SLOW] for duration >= 200ms."""
    result = profilers._get_warning_symbol(200.0)

    assert result == " [SLOW]"


def test_get_warning_symbol_normal():
    """Test _get_warning_symbol returns empty string for duration < 200ms."""
    result = profilers._get_warning_symbol(199.0)

    assert result == ""


def test_get_size_warning_symbol_both_none_returns_empty():
    assert profilers._get_size_warning_symbol(None, None) == ""


def test_get_size_warning_symbol_below_threshold_returns_empty(monkeypatch):
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=10.0))
    assert profilers._get_size_warning_symbol(5.0, 8.0) == ""


def test_get_size_warning_symbol_input_above_threshold(monkeypatch):
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=10.0))
    assert profilers._get_size_warning_symbol(15.0, 1.0) == " [BIG]"


def test_get_size_warning_symbol_output_above_threshold(monkeypatch):
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=10.0))
    assert profilers._get_size_warning_symbol(1.0, 20.0) == " [BIG]"


def test_get_size_warning_symbol_threshold_boundary(monkeypatch):
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=10.0))
    assert profilers._get_size_warning_symbol(10.0, None) == " [BIG]"


def test_get_size_warning_symbol_none_and_small(monkeypatch):
    monkeypatch.setattr(profilers, "_THRESHOLDS", Thresholds(size_big_tag_mb=10.0))
    assert profilers._get_size_warning_symbol(None, 0.5) == ""


def test_get_indent_ascii_fallback(monkeypatch):
    """Test get_indent produces ASCII output when constants are patched."""
    monkeypatch.setattr(profilers, "TOP_START", "+- ")
    monkeypatch.setattr(profilers, "TOP_END", "\\- ")
    monkeypatch.setattr(profilers, "PIPE", "|  ")
    monkeypatch.setattr(profilers, "NEST_START", "|- +- ")
    monkeypatch.setattr(profilers, "NEST_END", "|  \\- ")

    assert profilers.get_indent(0, is_start=True) == "+- "
    assert profilers.get_indent(0, is_start=False) == "\\- "
    assert profilers.get_indent(1, is_start=True) == "|- +- "
    assert profilers.get_indent(1, is_start=False) == "|  \\- "
    assert profilers.get_indent(2, is_start=True) == "|  |- +- "


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


_DEFAULT_THRESHOLDS = Thresholds()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.05, Style.DIM),
        (0.5, Fore.GREEN),
        (5.0, Fore.YELLOW),
        (50.0, Fore.RED + Style.BRIGHT),
    ],
)
def test_bucket_color_for_size(monkeypatch, value, expected):
    monkeypatch.setattr(profilers, "_THRESHOLDS", _DEFAULT_THRESHOLDS)
    assert profilers._bucket_color(value, _DEFAULT_THRESHOLDS.size_mb) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (50.0, Style.DIM),
        (300.0, Fore.GREEN),
        (700.0, Fore.YELLOW),
        (2000.0, Fore.RED + Style.BRIGHT),
    ],
)
def test_bucket_color_for_rss(monkeypatch, value, expected):
    monkeypatch.setattr(profilers, "_THRESHOLDS", _DEFAULT_THRESHOLDS)
    assert profilers._bucket_color(value, _DEFAULT_THRESHOLDS.rss_mb) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-50.0, Style.DIM),
        (-5.0, Style.DIM),
        (0.0, Style.DIM),
        (0.5, Style.DIM),
        (5.0, Fore.GREEN),
        (50.0, Fore.YELLOW),
        (500.0, Fore.RED + Style.BRIGHT),
    ],
)
def test_bucket_color_for_rss_delta(monkeypatch, value, expected):
    """Unified DIM/GREEN/YELLOW/RED ladder — negative/near-zero fall into ``< low`` → DIM."""
    monkeypatch.setattr(profilers, "_THRESHOLDS", _DEFAULT_THRESHOLDS)
    assert profilers._bucket_color(value, _DEFAULT_THRESHOLDS.rss_delta_mb) == expected
