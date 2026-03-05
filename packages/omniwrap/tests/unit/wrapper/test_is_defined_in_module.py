"""Tests for Wrapper._is_defined_in_module() method."""

import os

import pytest
from omniwrap.wrapper import Wrapper


def test_function_from_same_module():
    """Function defined in module should return True."""

    def func():
        pass

    func.__module__ = "my_module"

    assert Wrapper._is_defined_in_module(func, "my_module") is True


def test_class_from_same_module():
    """Class defined in module should return True."""

    class MyClass:
        pass

    MyClass.__module__ = "my_module"

    assert Wrapper._is_defined_in_module(MyClass, "my_module") is True


def test_lambda_from_same_module():
    """Lambda defined in test module should match its module name."""
    f = lambda: None  # noqa: E731
    assert Wrapper._is_defined_in_module(f, f.__module__) is True


def test_function_from_different_module():
    """Function from different module should return False."""

    def func():
        pass

    func.__module__ = "other_module"

    assert Wrapper._is_defined_in_module(func, "my_module") is False


def test_class_from_different_module():
    """Class from different module should return False."""

    class MyClass:
        pass

    MyClass.__module__ = "other_module"

    assert Wrapper._is_defined_in_module(MyClass, "my_module") is False


def test_lambda_from_different_module():
    """Lambda should return False for different module."""
    f = lambda: None  # noqa: E731
    assert Wrapper._is_defined_in_module(f, "other_module") is False


def test_imported_function():
    """Imported function should return False for importing module."""
    assert Wrapper._is_defined_in_module(os.path.join, "my_module") is False


@pytest.mark.parametrize(
    "obj",
    [
        pytest.param(42, id="int"),
        pytest.param(len, id="builtin_len"),
        pytest.param(str, id="builtin_str"),
        pytest.param(list, id="builtin_list"),
        pytest.param(None, id="None"),
    ],
)
def test_builtin_objects_return_false(obj):
    """Built-in/special objects should return False for user modules."""
    assert Wrapper._is_defined_in_module(obj, "my_module") is False
