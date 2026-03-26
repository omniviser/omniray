"""Dual-layer observability: console profiling + OpenTelemetry spans.

Important Notes:
- You can disable both - otel and console profiling - via flags
- Span timing/names ARE duplicated (telemetry + console) - this is intentional
- I/O logging (args/results) is ONLY in console - not sent to telemetry (too verbose)
- Colorama auto-strips colors in non-TTY environments unless OMNIRAY_LOG_COLOR=true
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from typing import TYPE_CHECKING

from omniray.tracing.console import logger, setup_console_handler
from omniray.tracing.flags import CONSOLE_LOG_FLAG, TraceFlags, resolve_trace_flags
from omniray.tracing.io_loggers import IOLogger
from omniray.tracing.otel import (
    HAS_OTEL,
    NOOP_CONTEXT,
    OTEL_FLAG,
    OTEL_MISSING_MSG,
    Status,
    StatusCode,
    otel_tracer,
)
from omniray.tracing.profilers import SpanProfiler
from omniray.tracing.span_name_generator import SpanNameGenerator

if TYPE_CHECKING:
    from collections.abc import Callable

    from opentelemetry.trace import Span as OtelSpan

    from omniray.types import CallResult, WraptInstance

# Context variable to track call depth for hierarchical logging
_call_depth: ContextVar[int] = ContextVar("trace_call_depth", default=0)

if CONSOLE_LOG_FLAG is True:
    setup_console_handler()


class Tracer:
    """Orchestrates console profiling and OpenTelemetry span creation."""

    profiler = SpanProfiler()
    io_logger = IOLogger()

    @classmethod
    def trace(  # noqa: PLR0913
        cls,
        wrapped: Callable,
        args: tuple,
        kwargs: dict,
        *,
        instance: WraptInstance = None,
        log: bool | None = None,
        log_input: bool | None = None,
        log_output: bool | None = None,
        otel: bool | None = None,
    ) -> CallResult:
        """Trace synchronous callable execution.

        Args:
            wrapped: The callable to trace.
            args: Positional arguments for *wrapped*.
            kwargs: Keyword arguments for *wrapped*.
            instance: The bound instance/class from wrapt (``None`` for ``@trace``).
            log: Override global OMNIRAY_LOG per-function.
            log_input: Override global OMNIRAY_LOG_INPUT per-function.
            log_output: Override global OMNIRAY_LOG_OUTPUT per-function.
            otel: Override global OMNIRAY_OTEL per-function.
        """
        flags = resolve_trace_flags(
            log=log, log_input=log_input, log_output=log_output, otel=otel, otel_flag=OTEL_FLAG
        )
        if flags.log:
            setup_console_handler()
        span_name, current_depth = cls._setup_trace(wrapped, args, kwargs, flags, instance=instance)
        try:
            if flags.otel and not HAS_OTEL:
                raise ImportError(OTEL_MISSING_MSG)
            # otel_tracer is guaranteed non-None here — guarded by flags.otel + HAS_OTEL check above
            context = otel_tracer.start_as_current_span(span_name) if flags.otel else NOOP_CONTEXT  # type: ignore[union-attr]
            with context as span:  # type: ignore[union-attr]
                start_time = cls._init_tracing(span, current_depth)
                duration_s = 0.0
                try:
                    result = wrapped(*args, **kwargs)
                except Exception as e:
                    duration_s = time.time() - start_time
                    try:  # noqa: SIM105 - tracing must never mask user exceptions
                        cls._finish_tracing_failure(
                            span, duration_s, span_name, current_depth, e, flags
                        )
                    except Exception:  # noqa: BLE001, S110
                        pass
                    raise
                else:
                    duration_s = time.time() - start_time
                    cls._finish_tracing(result, span_name, duration_s, current_depth, flags)
                    return result
                finally:
                    try:  # noqa: SIM105 - tracing must never mask user exceptions
                        cls._trace_duration(span, duration_s)
                    except Exception:  # noqa: BLE001, S110
                        pass
        finally:
            _call_depth.set(current_depth)

    @staticmethod
    def _init_tracing(span: OtelSpan | None, current_depth: int) -> float:
        """Initialize span attributes."""
        if span is not None:
            span.set_attribute("depth", current_depth)
        return time.time()

    @classmethod
    def _finish_tracing(
        cls,
        result: CallResult,
        span_name: str,
        duration_s: float,
        current_depth: int,
        flags: TraceFlags,
    ) -> None:
        """Handle successful trace completion."""
        if not flags.log:
            return
        duration_ms = duration_s * 1000
        cls.profiler.log_span_success(span_name, duration_ms, current_depth)
        if flags.log_output:
            cls.io_logger.log_output(result, current_depth)
        cls.profiler.log_section_separator(current_depth)

    @classmethod
    def _finish_tracing_failure(  # noqa: PLR0913
        cls,
        span: OtelSpan,
        duration_s: float,
        span_name: str,
        current_depth: int,
        exception: Exception,
        flags: TraceFlags,
    ) -> None:
        """Handle failed trace completion."""
        if flags.log:
            duration_ms = duration_s * 1000
            cls.profiler.log_span_failure(span_name, duration_ms, current_depth)
        if flags.otel:
            cls._trace_span_error(span, exception)

    @classmethod
    def _setup_trace(
        cls,
        wrapped: Callable,
        args: tuple,
        kwargs: dict,
        flags: TraceFlags,
        *,
        instance: WraptInstance = None,
    ) -> tuple[str, int]:
        """Setup tracing context before callable execution."""
        span_name = SpanNameGenerator.generate(wrapped, instance=instance)
        if not flags.log:
            return span_name, 0
        current_depth = cls._update_depth(span_name)
        if flags.log_input:
            cls.io_logger.log_input(args, kwargs, wrapped, current_depth)
        return span_name, current_depth

    @classmethod
    def _update_depth(cls, span_name: str) -> int:
        """Update call depth and log span start."""
        current_depth = _call_depth.get()
        _call_depth.set(current_depth + 1)
        indent = cls.profiler.get_indent(current_depth, is_start=True)
        logger.info("%s%s", indent, span_name)
        return current_depth

    @staticmethod
    def _trace_span_error(span: OtelSpan, exception: Exception) -> None:
        """Common error handling for spans."""
        span.set_attribute("error.type", exception.__class__.__name__)
        span.set_attribute("error.message", str(exception))
        span.record_exception(exception)
        # Status/StatusCode guaranteed non-None: only called when flags.otel is True
        span.set_status(Status(StatusCode.ERROR, str(exception)))  # type: ignore[misc, union-attr]

    @staticmethod
    def _trace_duration(span: OtelSpan | None, duration_s: float) -> None:
        """Set duration attribute on span."""
        if span is not None:
            span.set_attribute("duration_seconds", duration_s)


class AsyncTracer(Tracer):
    """Async variant of :class:`Tracer`."""

    @classmethod
    async def trace(  # noqa: PLR0913
        cls,
        wrapped: Callable,
        args: tuple,
        kwargs: dict,
        *,
        instance: WraptInstance = None,
        log: bool | None = None,
        log_input: bool | None = None,
        log_output: bool | None = None,
        otel: bool | None = None,
    ) -> CallResult:
        """Trace asynchronous callable execution.

        Args:
            wrapped: The callable to trace.
            args: Positional arguments for *wrapped*.
            kwargs: Keyword arguments for *wrapped*.
            instance: The bound instance/class from wrapt (``None`` for ``@trace``).
            log: Override global OMNIRAY_LOG per-function.
            log_input: Override global OMNIRAY_LOG_INPUT per-function.
            log_output: Override global OMNIRAY_LOG_OUTPUT per-function.
            otel: Override global OMNIRAY_OTEL per-function.
        """
        flags = resolve_trace_flags(
            log=log, log_input=log_input, log_output=log_output, otel=otel, otel_flag=OTEL_FLAG
        )
        if flags.log:
            setup_console_handler()
        span_name, current_depth = cls._setup_trace(wrapped, args, kwargs, flags, instance=instance)
        try:
            if flags.otel and not HAS_OTEL:
                raise ImportError(OTEL_MISSING_MSG)
            span, token = cls._enter_otel_span(span_name, flags)
            try:
                start_time = cls._init_tracing(span, current_depth)
                duration_s = 0.0
                try:
                    result = await wrapped(*args, **kwargs)
                except Exception as e:
                    duration_s = time.time() - start_time
                    try:  # noqa: SIM105 - tracing must never mask user exceptions
                        cls._finish_tracing_failure(
                            span, duration_s, span_name, current_depth, e, flags
                        )
                    except Exception:  # noqa: BLE001, S110
                        pass
                    raise
                else:
                    duration_s = time.time() - start_time
                    cls._finish_tracing(result, span_name, duration_s, current_depth, flags)
                    return result
                finally:
                    try:  # noqa: SIM105 - tracing must never mask user exceptions
                        cls._trace_duration(span, duration_s)
                    except Exception:  # noqa: BLE001, S110
                        pass
            finally:
                cls._exit_otel_span(span, token, flags)
        finally:
            _call_depth.set(current_depth)

    @staticmethod
    def _enter_otel_span(span_name: str, flags: TraceFlags) -> tuple:
        """Start an OTel span with explicit attach — no generator, safe for async GC."""
        if not flags.otel:
            return None, None
        from opentelemetry import context as context_api  # noqa: PLC0415
        from opentelemetry import trace as trace_api  # noqa: PLC0415

        # otel_tracer guaranteed non-None: guarded by flags.otel + HAS_OTEL
        span = otel_tracer.start_span(span_name)  # type: ignore[union-attr]
        ctx = trace_api.set_span_in_context(span)
        token = context_api.attach(ctx)
        return span, token

    @staticmethod
    def _exit_otel_span(span: OtelSpan | None, token: object | None, flags: TraceFlags) -> None:
        """Detach context and end span. Counterpart to :meth:`_enter_otel_span`."""
        if not flags.otel:
            return
        from opentelemetry import context as context_api  # noqa: PLC0415

        context_api.detach(token)  # type: ignore[arg-type]  # Token[Context] stored as object
        span.end()  # type: ignore[union-attr]
