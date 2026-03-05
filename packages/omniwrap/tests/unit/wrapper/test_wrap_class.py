"""Tests for Wrapper._wrap_class() method."""

import functools

import pytest
import wrapt
from omniwrap.wrapper import Wrapper


def test_wraps_regular_method(mocker, mock_wrappers_list):
    """Regular methods should be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        def method(self):
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(MyClass, "method", mock_wrappers_list[0])


def test_wraps_multiple_methods(mocker, mock_wrappers_list):
    """All regular methods should be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        def method1(self):
            pass

        def method2(self):
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    expected_call_count = 2
    assert mock_wrap_callable.call_count == expected_call_count
    called_names = {call[0][1] for call in mock_wrap_callable.call_args_list}
    assert called_names == {"method1", "method2"}


def test_wraps_classmethod(mocker, mock_wrappers_list):
    """Classmethods should be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        @classmethod
        def class_method(cls):
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(MyClass, "class_method", mock_wrappers_list[0])


def test_wraps_staticmethod(mocker, mock_wrappers_list):
    """Staticmethods should be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        @staticmethod
        def static_method():
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(MyClass, "static_method", mock_wrappers_list[0])


def test_wraps_private_method(mocker, mock_wrappers_list):
    """_private methods should be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        def _private_method(self):
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(MyClass, "_private_method", mock_wrappers_list[0])


@pytest.mark.parametrize(
    "dunder_name",
    [
        pytest.param("__init__", id="init"),
        pytest.param("__str__", id="str"),
    ],
)
def test_skips_dunder_methods(mocker, mock_wrappers_list, dunder_name):
    """Dunder methods should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    cls = type("MyClass", (), {dunder_name: lambda _self: None})

    Wrapper._wrap_class(cls, mock_wrappers_list)

    mock_wrap_callable.assert_not_called()


def test_skips_property(mocker, mock_wrappers_list):
    """Properties should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        @property
        def prop(self):
            return "value"

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_not_called()


def test_skips_nested_exception(mocker, mock_wrappers_list):
    """Nested exception classes should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        class NestedError(Exception):
            pass

        def method(self):
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(MyClass, "method", mock_wrappers_list[0])


def test_skips_class_attribute(mocker, mock_wrappers_list):
    """Non-callable class attributes should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        class_attr = "not callable"

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_not_called()


def test_wraps_method_with_functools_wraps(mocker, mock_wrappers_list):
    """Methods decorated with @functools.wraps should still be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    def original(self):
        pass

    @functools.wraps(original)
    def wrapped(self):
        return original(self)

    class MyClass:
        method = wrapped

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_called_once()


def test_skips_already_wrapped_by_wrapt(mocker, mock_wrappers_list):
    """Methods already wrapped by wrapt (FunctionWrapper) should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    def original(self):
        pass

    wrapt_wrapped = wrapt.FunctionWrapper(original, lambda w, _i, a, k: w(*a, **k))

    class MyClass:
        method = wrapt_wrapped

    Wrapper._wrap_class(MyClass, mock_wrappers_list)

    mock_wrap_callable.assert_not_called()


def test_does_not_wrap_inherited_methods(mocker, mock_wrappers_list):
    """Inherited methods should NOT be wrapped (uses vars(), not dir())."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class Base:
        def base_method(self):
            pass

    class Derived(Base):
        def derived_method(self):
            pass

    Wrapper._wrap_class(Derived, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(Derived, "derived_method", mock_wrappers_list[0])


def test_skips_excluded_methods(mocker, mock_wrappers_list):
    """Methods in skip_wrap should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    class MyClass:
        def to_pydantic(self):
            pass

        def process(self):
            pass

    Wrapper._wrap_class(MyClass, mock_wrappers_list, skip_wrap=frozenset({"to_pydantic"}))

    mock_wrap_callable.assert_called_once_with(MyClass, "process", mock_wrappers_list[0])
