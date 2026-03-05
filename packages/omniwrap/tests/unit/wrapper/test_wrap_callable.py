"""Tests for Wrapper._wrap_callable() method."""

from types import ModuleType

import wrapt
from omniwrap import wrapper as wrapper_module
from omniwrap.wrapper import Wrapper


def test_sync_function_uses_sync_wrapper(mocker, mock_wrappers):
    """Sync function should use sync_wrapper (first in tuple)."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    def sync_func():
        pass

    module = ModuleType("test_module")
    module.sync_func = sync_func

    Wrapper._wrap_callable(module, "sync_func", mock_wrappers)

    mock_wrapt.assert_called_once_with(module, "sync_func", mock_wrappers[0])


def test_async_function_uses_async_wrapper(mocker, mock_wrappers):
    """Async function should use async_wrapper (second in tuple)."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    async def async_func():
        pass

    module = ModuleType("test_module")
    module.async_func = async_func

    Wrapper._wrap_callable(module, "async_func", mock_wrappers)

    mock_wrapt.assert_called_once_with(module, "async_func", mock_wrappers[1])


def test_classmethod_uses_sync_wrapper(mocker, mock_wrappers):
    """Classmethod should use sync_wrapper."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    class MyClass:
        @classmethod
        def class_method(cls):
            pass

    Wrapper._wrap_callable(MyClass, "class_method", mock_wrappers)

    mock_wrapt.assert_called_once_with(MyClass, "class_method", mock_wrappers[0])


def test_staticmethod_uses_sync_wrapper(mocker, mock_wrappers):
    """Staticmethod should use sync_wrapper."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    class MyClass:
        @staticmethod
        def static_method():
            pass

    Wrapper._wrap_callable(MyClass, "static_method", mock_wrappers)

    mock_wrapt.assert_called_once_with(MyClass, "static_method", mock_wrappers[0])


def test_async_classmethod_uses_async_wrapper(mocker, mock_wrappers):
    """Async classmethod should use async_wrapper."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    class MyClass:
        @classmethod
        async def async_class_method(cls):
            pass

    Wrapper._wrap_callable(MyClass, "async_class_method", mock_wrappers)

    mock_wrapt.assert_called_once_with(MyClass, "async_class_method", mock_wrappers[1])


def test_type_error_handled_silently(mocker, test_module, mock_wrappers):
    """TypeError from wrapt should be handled silently."""
    mocker.patch.object(wrapt, "wrap_function_wrapper", side_effect=TypeError("cannot wrap"))

    def func():
        pass

    test_module.func = func

    Wrapper._wrap_callable(test_module, "func", mock_wrappers)


def test_attribute_error_handled_silently(mocker, test_module, mock_wrappers):
    """AttributeError from wrapt should be handled silently."""
    mocker.patch.object(wrapt, "wrap_function_wrapper", side_effect=AttributeError("no attr"))

    def func():
        pass

    test_module.func = func

    Wrapper._wrap_callable(test_module, "func", mock_wrappers)


def test_logs_debug_on_success(mocker, test_module, mock_wrappers):
    """Should log debug message on successful wrap."""
    mocker.patch.object(wrapt, "wrap_function_wrapper")
    mock_logger = mocker.patch.object(wrapper_module, "logger")

    def func():
        pass

    test_module.func = func

    Wrapper._wrap_callable(test_module, "func", mock_wrappers)

    mock_logger.debug.assert_called_once()
    call_args = mock_logger.debug.call_args
    assert "Wrapped" in call_args[0][0]
    assert "test_module" in call_args[0][1]
    assert "func" in call_args[0][2]


def test_none_sync_wrapper_skipped(mocker, test_module):
    """None sync wrapper should skip wrapping without error."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    def func():
        pass

    test_module.func = func

    Wrapper._wrap_callable(test_module, "func", (None, mocker.MagicMock()))

    mock_wrapt.assert_not_called()


def test_none_async_wrapper_skipped(mocker, test_module):
    """None async wrapper should skip wrapping without error."""
    mock_wrapt = mocker.patch.object(wrapt, "wrap_function_wrapper")

    async def async_func():
        pass

    test_module.async_func = async_func

    Wrapper._wrap_callable(test_module, "async_func", (mocker.MagicMock(), None))

    mock_wrapt.assert_not_called()
