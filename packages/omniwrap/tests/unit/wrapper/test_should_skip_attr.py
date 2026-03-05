"""Tests for Wrapper._should_skip_attr() method."""

import functools

import pytest
import wrapt
from omniwrap.wrapper import Wrapper


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("__init__", id="init"),
        pytest.param("__str__", id="str"),
        pytest.param("__repr__", id="repr"),
        pytest.param("__call__", id="call"),
        pytest.param("__eq__", id="eq"),
        pytest.param("__hash__", id="hash"),
    ],
)
def test_skip_dunder_methods(name):
    """Dunder methods should be skipped."""

    def method(self):
        pass

    assert Wrapper._should_skip_attr(name, method) is True


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("_private", id="single_prefix"),
        pytest.param("method_", id="single_suffix"),
        pytest.param("__private", id="double_prefix_only"),
    ],
)
def test_not_skip_non_dunder_underscores(name):
    """Non-dunder underscore names should NOT be skipped."""

    def method(self):
        pass

    assert Wrapper._should_skip_attr(name, method) is False


def test_skip_property():
    """Properties should be skipped."""
    prop = property(lambda _self: "value")
    assert Wrapper._should_skip_attr("my_prop", prop) is True


def test_skip_property_with_setter():
    """Properties with setters should also be skipped."""
    prop = property(lambda _self: "value", lambda _self, _v: None)
    assert Wrapper._should_skip_attr("my_prop", prop) is True


@pytest.mark.parametrize(
    "exc_class",
    [
        pytest.param(type("NestedError", (Exception,), {}), id="Exception"),
        pytest.param(type("NestedKI", (KeyboardInterrupt,), {}), id="KeyboardInterrupt"),
        pytest.param(type("CustomVE", (ValueError,), {}), id="ValueError"),
    ],
)
def test_skip_nested_exception_classes(exc_class):
    """Nested exception classes should be skipped."""
    assert Wrapper._should_skip_attr("Error", exc_class) is True


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("string", id="string"),
        pytest.param(42, id="int"),
        pytest.param([1, 2, 3], id="list"),
        pytest.param({"k": "v"}, id="dict"),
        pytest.param(None, id="None"),
    ],
)
def test_skip_non_callable_attributes(value):
    """Non-callable class attributes should be skipped."""
    assert Wrapper._should_skip_attr("attr", value) is True


def test_not_skip_functools_wrapped():
    """Functions with __wrapped__ from functools.wraps should NOT be skipped."""

    def original():
        pass

    @functools.wraps(original)
    def wrapper():
        return original()

    assert Wrapper._should_skip_attr("wrapper", wrapper) is False


def test_skip_wrapt_function_wrapper():
    """Functions already wrapped by wrapt (FunctionWrapper) should be skipped."""

    def original():
        pass

    wrapt_wrapped = wrapt.FunctionWrapper(original, lambda w, _i, a, k: w(*a, **k))
    assert Wrapper._should_skip_attr("method", wrapt_wrapped) is True


def test_not_skip_unwrapped():
    """Functions without __wrapped__ should NOT be skipped."""

    def func():
        pass

    assert Wrapper._should_skip_attr("func", func) is False


def test_not_skip_regular_method():
    """Regular methods should NOT be skipped."""

    def method(self):
        pass

    assert Wrapper._should_skip_attr("method", method) is False


def test_not_skip_classmethod():
    """Classmethods should NOT be skipped."""

    class MyClass:
        @classmethod
        def class_method(cls):
            pass

    cm = vars(MyClass)["class_method"]
    assert Wrapper._should_skip_attr("class_method", cm) is False


def test_not_skip_staticmethod():
    """Staticmethods should NOT be skipped."""

    class MyClass:
        @staticmethod
        def static_method():
            pass

    sm = vars(MyClass)["static_method"]
    assert Wrapper._should_skip_attr("static_method", sm) is False


def test_not_skip_async_method():
    """Async methods should NOT be skipped."""

    async def async_method(self):
        pass

    assert Wrapper._should_skip_attr("async_method", async_method) is False


def test_skip_excluded_method():
    """Methods in skip_wrap should be skipped."""

    def to_pydantic(self):
        pass

    assert (
        Wrapper._should_skip_attr("to_pydantic", to_pydantic, skip_wrap=frozenset({"to_pydantic"}))
        is True
    )


def test_not_skip_method_not_in_skip_wrap():
    """Methods NOT in skip_wrap should not be skipped."""

    def process(self):
        pass

    assert (
        Wrapper._should_skip_attr("process", process, skip_wrap=frozenset({"to_pydantic"})) is False
    )


def test_not_skip_when_skip_wrap_empty():
    """Empty skip_wrap should not skip anything."""

    def to_pydantic(self):
        pass

    result = Wrapper._should_skip_attr("to_pydantic", to_pydantic, skip_wrap=frozenset())
    assert result is False
