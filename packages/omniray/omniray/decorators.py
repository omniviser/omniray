"""Decorators and wrappers for tracing function execution.

This module provides:
- trace() decorator for manual instrumentation
- create_trace_wrapper() factory for automatic instrumentation with omniwrap
"""

import asyncio
from collections.abc import Callable
from functools import wraps

from omniray.tracing.tracers import (
    AsyncTracer,
    Tracer,
)
from omniray.types import CallResult, WraptInstance


def _exclude_from_omniwrap[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """Mark function as already traced so omniwrap won't double-wrap it.

    Sets ``_omniwrap_skip`` — the same attribute that ``@skip_wrap`` uses.
    type: ignore because plain functions don't declare this attribute in their type.
    """
    func._omniwrap_skip = True  # type: ignore[attr-defined]  # noqa: SLF001
    return func


def trace[**P, T](
    *,
    log: bool | None = None,
    log_input: bool | None = None,
    log_output: bool | None = None,
    skip_if: Callable[..., bool] | None = None,
    otel: bool | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to trace any function/method (sync/async) execution.

    Use this for manual instrumentation of specific functions.
    For automatic instrumentation of your entire codebase, use
    ``create_trace_wrapper()`` with ``omniwrap.wrap_all()``.

    Args:
        log: Override global OMNIRAY_LOG setting per-function.
        log_input: Override global OMNIRAY_LOG_INPUT setting.
        log_output: Override global OMNIRAY_LOG_OUTPUT setting.
        skip_if: Predicate receiving the decorated function's arguments.
            When it returns ``True``, tracing is bypassed entirely and the
            function is called directly.
        otel: Whether to create otel spans from the callable.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> CallResult:
                if skip_if is not None and skip_if(*args, **kwargs):
                    return await func(*args, **kwargs)
                return await AsyncTracer.trace(
                    func,
                    args,
                    kwargs,
                    log=log,
                    log_input=log_input,
                    log_output=log_output,
                    otel=otel,
                )

            # mypy can't prove async_wrapper satisfies Callable[P, T] because the
            # inner return type is CallResult (Any), not T.  @wraps preserves the
            # original signature at runtime; ParamSpec preserves it for callers.
            return _exclude_from_omniwrap(async_wrapper)  # type: ignore[return-value, arg-type]

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> CallResult:
            if skip_if is not None and skip_if(*args, **kwargs):
                return func(*args, **kwargs)
            return Tracer.trace(
                func,
                args,
                kwargs,
                log=log,
                log_input=log_input,
                log_output=log_output,
                otel=otel,
            )

        return _exclude_from_omniwrap(sync_wrapper)  # type: ignore[return-value]

    return decorator


def create_trace_wrapper(
    *,
    log: bool | None = None,
    log_input: bool | None = None,
    log_output: bool | None = None,
    skip_if: Callable[..., bool] | None = None,
    otel: bool | None = None,
) -> tuple[Callable, Callable]:
    """Create sync and async wrappers for tracing with wrapt.

    Args:
        log: Override global OMNIRAY_LOG setting.
        log_input: Override global OMNIRAY_LOG_INPUT setting.
        log_output: Override global OMNIRAY_LOG_OUTPUT setting.
        skip_if: Predicate receiving the wrapped function's arguments.
            When it returns ``True``, tracing is bypassed entirely and the
            function is called directly.  Note: wrapt separates ``self``/``cls``
            into a dedicated ``instance`` parameter, so the predicate receives
            only the explicit arguments (without ``self``).
        otel: Override global OMNIRAY_OTEL setting.

    Returns:
        Tuple of (sync_wrapper, async_wrapper) for use with omniwrap.
    """

    def sync_wrapper(
        wrapped: Callable, instance: WraptInstance, args: tuple, kwargs: dict
    ) -> CallResult:
        if skip_if is not None and skip_if(*args, **kwargs):
            return wrapped(*args, **kwargs)
        return Tracer.trace(
            wrapped,
            args,
            kwargs,
            instance=instance,
            log=log,
            log_input=log_input,
            log_output=log_output,
            otel=otel,
        )

    async def async_wrapper(
        wrapped: Callable, instance: WraptInstance, args: tuple, kwargs: dict
    ) -> CallResult:
        if skip_if is not None and skip_if(*args, **kwargs):
            return await wrapped(*args, **kwargs)
        return await AsyncTracer.trace(
            wrapped,
            args,
            kwargs,
            instance=instance,
            log=log,
            log_input=log_input,
            log_output=log_output,
            otel=otel,
        )

    return sync_wrapper, async_wrapper
