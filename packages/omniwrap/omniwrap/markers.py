"""Marker decorators for controlling wrap behavior."""

from collections.abc import Callable


def skip_wrap[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """Mark a function or class to be skipped by ``wrap_all()``.

    Example::

        from omniwrap import skip_wrap, wrap_all

        @skip_wrap
        def healthcheck():
            return "ok"

        wrap_all(my_wrapper)  # healthcheck will NOT be wrapped
    """
    func._omniwrap_skip = True  # type: ignore[attr-defined]  # noqa: SLF001
    return func
