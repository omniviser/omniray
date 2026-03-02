"""Tests for @skip_wrap marker — _should_skip_attr() and _wrap_object() integration."""

from omniwrap.markers import skip_wrap
from omniwrap.wrapper import Wrapper


def test_skip_marked_with_skip_wrap():
    """Methods decorated with @skip_wrap should be skipped."""

    @skip_wrap
    def method(self):
        pass

    assert Wrapper._should_skip_attr("method", method) is True


def test_skip_classmethod_with_skip_wrap():
    """Classmethods decorated with @skip_wrap should be skipped."""

    class MyClass:
        @classmethod
        @skip_wrap
        def class_method(cls):
            pass

    cm = vars(MyClass)["class_method"]
    assert Wrapper._should_skip_attr("class_method", cm) is True


def test_skip_staticmethod_with_skip_wrap():
    """Staticmethods decorated with @skip_wrap should be skipped."""

    class MyClass:
        @staticmethod
        @skip_wrap
        def static_method():
            pass

    sm = vars(MyClass)["static_method"]
    assert Wrapper._should_skip_attr("static_method", sm) is True


def test_skip_async_method_with_skip_wrap():
    """Async methods decorated with @skip_wrap should be skipped."""

    @skip_wrap
    async def async_method(self):
        pass

    assert Wrapper._should_skip_attr("async_method", async_method) is True


def test_skip_function_marked_skip_wrap(mocker, test_module, mock_wrappers_list):
    """Functions decorated with @skip_wrap should NOT be wrapped."""
    mock_wrap_callable = mocker.patch.object(Wrapper, "_wrap_callable")

    @skip_wrap
    def my_func():
        pass

    Wrapper._wrap_object(test_module, "my_func", my_func, mock_wrappers_list)

    mock_wrap_callable.assert_not_called()


def test_skip_class_marked_skip_wrap(mocker, test_module, mock_wrappers_list):
    """Classes decorated with @skip_wrap should NOT be wrapped."""
    mock_wrap_class = mocker.patch.object(Wrapper, "_wrap_class")

    @skip_wrap
    class MyClass:
        def method(self):
            pass

    Wrapper._wrap_object(test_module, "MyClass", MyClass, mock_wrappers_list)

    mock_wrap_class.assert_not_called()
