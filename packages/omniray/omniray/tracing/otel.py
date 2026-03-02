"""OpenTelemetry initialization and configuration."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING

from omniray.tracing.flags import _env_flag

if TYPE_CHECKING:
    from opentelemetry.trace import StatusCode as _StatusCodeType
    from opentelemetry.trace import Tracer as _TracerType
    from opentelemetry.trace.status import Status as _StatusType


@dataclass(frozen=True)
class OtelConfig:
    """OpenTelemetry configuration resolved at import time."""

    has_otel: bool
    tracer: _TracerType | None
    noop_context: object
    status: type[_StatusType] | None
    status_code: type[_StatusCodeType] | None
    span_type: type | None


def _init_otel(*, module_name: str) -> OtelConfig:
    """Initialize OpenTelemetry integration if available."""
    try:
        from opentelemetry import trace as api  # noqa: PLC0415
        from opentelemetry.trace import INVALID_SPAN  # noqa: PLC0415
        from opentelemetry.trace import Span as _OtelSpan  # noqa: PLC0415
        from opentelemetry.trace import Status as _Status  # noqa: PLC0415
        from opentelemetry.trace import StatusCode as _StatusCode  # noqa: PLC0415

        return OtelConfig(
            has_otel=True,
            tracer=api.get_tracer(module_name),
            noop_context=nullcontext(INVALID_SPAN),
            status=_Status,
            status_code=_StatusCode,
            span_type=_OtelSpan,
        )
    except ImportError:
        return OtelConfig(
            has_otel=False,
            tracer=None,
            noop_context=nullcontext(None),
            status=None,
            status_code=None,
            span_type=None,
        )


OTEL_MISSING_MSG = (
    "OpenTelemetry is required but not installed. Install with: pip install omniray[otel]"
)


def _check_otel_env(*, flag: bool | None, has_otel: bool) -> bool | None:
    """Validate OTel flag against availability.

    Raises ``ImportError`` only when OTel is explicitly enabled (``True``)
    but the package is not installed.
    """
    if flag is True and not has_otel:
        raise ImportError(OTEL_MISSING_MSG)
    return flag


_otel = _init_otel(module_name="omniray.tracing.tracers")
HAS_OTEL = _otel.has_otel
otel_tracer = _otel.tracer
NOOP_CONTEXT = _otel.noop_context
Status = _otel.status
StatusCode = _otel.status_code
OtelSpan = _otel.span_type

OTEL_FLAG = _check_otel_env(flag=_env_flag("OMNIRAY_OTEL"), has_otel=HAS_OTEL)
