"""Flag parsing and resolution for configuration.

Provides env var reading and global/local flag merging with kill-switch semantics.
"""

import os
from dataclasses import dataclass


def _env_flag(var: str) -> bool | None:
    """Read env var as bool, or None if unset."""
    raw = os.getenv(var)
    return raw.lower() in ("true", "1", "yes") if raw is not None else None


def resolve_flag(*, global_flag: bool | None, local_flag: bool | None) -> bool:
    """Resolve global (env var) and local (decorator) flag into a single bool."""
    if global_flag is False:
        return False
    if local_flag is not None:
        return local_flag
    return global_flag is True


CONSOLE_LOG_FLAG = _env_flag("OMNIRAY_LOG")
LOG_INPUT_FLAG = _env_flag("OMNIRAY_LOG_INPUT")
LOG_OUTPUT_FLAG = _env_flag("OMNIRAY_LOG_OUTPUT")


@dataclass(frozen=True)
class TraceFlags:
    """Resolved trace flags — all ``bool``, no more ``None``."""

    log: bool
    log_input: bool
    log_output: bool
    otel: bool


_default_flags_cache: dict[bool | None, TraceFlags] = {}


def resolve_trace_flags(
    *,
    log: bool | None,
    log_input: bool | None,
    log_output: bool | None,
    otel: bool | None,
    otel_flag: bool | None,
) -> TraceFlags:
    """Resolve all flags into concrete bools for a single trace call.

    When all local overrides are None (the common case with ``wrap_all``),
    returns a cached singleton — avoids repeated flag resolution and dataclass
    allocation on every call.
    """
    if log is None and log_input is None and log_output is None and otel is None:
        cached = _default_flags_cache.get(otel_flag)
        if cached is not None:
            return cached
        flags = _resolve_all(
            log=None, log_input=None, log_output=None, otel=None, otel_flag=otel_flag
        )
        _default_flags_cache[otel_flag] = flags
        return flags
    return _resolve_all(
        log=log, log_input=log_input, log_output=log_output, otel=otel, otel_flag=otel_flag
    )


def _resolve_all(
    *,
    log: bool | None,
    log_input: bool | None,
    log_output: bool | None,
    otel: bool | None,
    otel_flag: bool | None,
) -> TraceFlags:
    should_log = resolve_flag(global_flag=CONSOLE_LOG_FLAG, local_flag=log)
    return TraceFlags(
        log=should_log,
        log_input=resolve_flag(global_flag=LOG_INPUT_FLAG, local_flag=log_input) and should_log,
        log_output=resolve_flag(global_flag=LOG_OUTPUT_FLAG, local_flag=log_output) and should_log,
        otel=resolve_flag(global_flag=otel_flag, local_flag=otel),
    )
