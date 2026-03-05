"""Tests for Wrapper._wrap_object() method."""

import pytest
import wrapt
from omniwrap.wrapper import Wrapper


@pytest.mark.parametrize(
    "exc_class",
    [
        pytest.param(type("MyException", (Exception,), {}), id="Exception"),
        pytest.param(type("MyKeyboardInterrupt", (KeyboardInterrupt,), {}), id="KeyboardInterrupt"),
        pytest.param(type("CustomValueError", (ValueError,), {}), id="ValueError"),
    ],
)
def test_skip_exception_classes(mocker, test_module, mock_wrappers_list, exc_class):
    """Exception classes should be skipped, not wrapped."""
    mock_wrap_class = mocker.patch.object(Wrapper, "_wrap_class")

    Wrapper._wrap_object(test_module, exc_class.__name__, exc_class, mock_wrappers_list)

    mock_wrap_class.assert_not_called()


def test_wrap_regular_class(mocker, test_module, mock_wrappers_list):
    """Regular classes should be wrapped via _wrap_class."""
    mock_wrap_class = mocker.patch.object(Wrapper, "_wrap_class")

    class MyClass:
        pass

    Wrapper._wrap_object(test_module, "MyClass", MyClass, mock_wrappers_list)

    mock_wrap_class.assert_called_once_with(MyClass, mock_wrappers_list, skip_wrap=frozenset())


def test_wrap_class_passes_skip_wrap(mocker, test_module, mock_wrappers_list):
    """skip_wrap should be forwarded to _wrap_class."""
    mock_wrap_class = mocker.patch.object(Wrapper, "_wrap_class")

    class MyClass:
        pass

    exclude = frozenset({"to_pydantic"})
    Wrapper._wrap_object(test_module, "MyClass", MyClass, mock_wrappers_list, skip_wrap=exclude)

    mock_wrap_class.assert_called_once_with(MyClass, mock_wrappers_list, skip_wrap=exclude)


def test_wrap_regular_function(mocker, test_module, mock_wrappers_list):
    """Regular functions should be wrapped via _wrap_callable for each wrapper pair."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    def my_func():
        pass

    Wrapper._wrap_object(test_module, "my_func", my_func, mock_wrappers_list)

    mock_wrap_callable.assert_called_once_with(test_module, "my_func", mock_wrappers_list[0])


def test_wraps_function_with_functools_wrapped(mocker, test_module, mock_wrappers_list):
    """Functions with __wrapped__ from functools.wraps should still be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    def my_func():
        pass

    my_func.__wrapped__ = lambda: None

    Wrapper._wrap_object(test_module, "my_func", my_func, mock_wrappers_list)

    mock_wrap_callable.assert_called_once()


def test_skip_already_wrapped_by_wrapt(mocker, test_module, mock_wrappers_list):
    """Functions already wrapped by wrapt (FunctionWrapper) should be skipped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    def my_func():
        pass

    wrapt_wrapped = wrapt.FunctionWrapper(my_func, lambda w, _i, a, k: w(*a, **k))

    Wrapper._wrap_object(test_module, "my_func", wrapt_wrapped, mock_wrappers_list)

    mock_wrap_callable.assert_not_called()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        pytest.param("my_string", "not callable", id="string"),
        pytest.param("count", 42, id="int"),
    ],
)
def test_skip_non_callable(mocker, test_module, mock_wrappers_list, name, value):
    """Non-callable objects should be skipped."""
    mock_wrap_class = mocker.patch.object(Wrapper, "_wrap_class")
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    Wrapper._wrap_object(test_module, name, value, mock_wrappers_list)

    mock_wrap_class.assert_not_called()
    mock_wrap_callable.assert_not_called()
