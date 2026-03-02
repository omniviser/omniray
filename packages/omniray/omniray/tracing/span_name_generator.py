"""Utilities for generating OpenTelemetry span names."""

from collections.abc import Callable

from omniray.types import WraptInstance


class SpanNameGenerator:
    """Utility class for generating span names."""

    @classmethod
    def generate(cls, wrapped: Callable, *, instance: WraptInstance = None) -> str:
        """Generate span name based on callable type.

        Resolution order:
        1. **wrapt instance** — most reliable: the bound object/class from wrapt.
        2. **__qualname__** — fallback for ``@trace`` decorator, staticmethods,
           and standalone functions.  Always correct because Python tracks the
           defining class (e.g. ``OrderService._get_or_create_draft``).
        """
        if instance is not None:
            return cls._get_span_name_from_instance(wrapped, instance)
        return cls._get_span_name_from_qualname(wrapped)

    @staticmethod
    def _get_span_name_from_instance(wrapped: Callable, instance: WraptInstance) -> str:
        """Generate span name when wrapt provides the instance separately."""
        class_name = instance.__name__ if isinstance(instance, type) else type(instance).__name__
        return f"{class_name}.{wrapped.__name__}"

    @staticmethod
    def _get_span_name_from_qualname(wrapped: Callable) -> str:
        """Generate span name from ``__qualname__``.

        Handles methods (``Class.method``), nested classes (``Outer.Inner.method``),
        and plain functions (``func``).  Strips ``<locals>.`` segments that appear
        for closures/inner functions.
        """
        qualname = wrapped.__qualname__
        # Remove <locals> segments: "func.<locals>.inner" → "func.inner"
        parts = [p for p in qualname.split(".") if p != "<locals>"]
        return ".".join(parts)
