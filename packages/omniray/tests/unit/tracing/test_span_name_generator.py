"""Tests for span name generator module."""

from omniray.tracing.span_name_generator import SpanNameGenerator

# ── Test helpers (module-level so __qualname__ is clean) ─────────────


def _get_user_by_id():
    pass


class OrderService:
    def _validate_items(self):
        pass

    @classmethod
    def create_from_cart(cls):
        pass

    @staticmethod
    def _get_or_create_draft(order_id):
        pass


def _outer():
    def _inner():
        pass

    return _inner


_nested_inner = _outer()


# ── instance path (wrapt) ────────────────────────────────────────────


def test_instance_method():
    """Instance param resolves class name from the bound object."""

    class MyView:
        pass

    instance = MyView()

    def wrapped():
        pass

    wrapped.__name__ = "handle"

    result = SpanNameGenerator.generate(wrapped, instance=instance)

    assert result == "MyView.handle"


def test_classmethod_instance():
    """For classmethods, wrapt passes the class itself as instance."""

    class AuthService:
        pass

    def wrapped():
        pass

    wrapped.__name__ = "authenticate"

    result = SpanNameGenerator.generate(wrapped, instance=AuthService)

    assert result == "AuthService.authenticate"


# ── qualname path (no instance) ──────────────────────────────────────


def test_standalone_function():
    """Standalone function — __qualname__ equals __name__."""
    result = SpanNameGenerator.generate(_get_user_by_id)

    assert result == "_get_user_by_id"


def test_method_via_trace_decorator():
    """@trace on a method — __qualname__ includes the defining class."""
    result = SpanNameGenerator.generate(OrderService._validate_items)

    assert result == "OrderService._validate_items"


def test_classmethod_via_trace_decorator():
    """@trace on a classmethod — __qualname__ gives class, not 'type'."""
    result = SpanNameGenerator.generate(OrderService.create_from_cart)

    assert result == "OrderService.create_from_cart"


def test_staticmethod_via_omniwrap():
    """Staticmethod wrapped by omniwrap — instance=None, __qualname__ has class."""
    result = SpanNameGenerator.generate(OrderService._get_or_create_draft)

    assert result == "OrderService._get_or_create_draft"


def test_nested_function_strips_locals():
    """Closures have <locals> in __qualname__ — strip it for readability."""
    result = SpanNameGenerator.generate(_nested_inner)

    assert result == "_outer._inner"
