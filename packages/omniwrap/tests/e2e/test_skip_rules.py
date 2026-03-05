"""E2E tests for skip rules — exceptions, dunders, properties must NOT be wrapped."""

import asyncio

from omniwrap.wrapper import Wrapper

MODULE_WITH_EXCEPTION = """
class ServiceError(Exception):
    pass

class Service:
    def process(self):
        return "ok"
"""

MODULE_WITH_NESTED_EXCEPTION = """
class Service:
    class NotFoundError(Exception):
        pass

    def get(self, item_id):
        return f"item {item_id}"
"""

MODULE_WITH_BASE_EXCEPTION = """
class FatalError(BaseException):
    pass

class Service:
    def run(self):
        return "running"
"""

MODULE_WITH_DUNDERS_AND_PROPERTIES = """
class Service:
    def __init__(self, name):
        self._name = name

    def __str__(self):
        return f"Service({self._name})"

    def __repr__(self):
        return f"Service({self._name!r})"

    @property
    def name(self):
        return self._name

    def process(self):
        return f"processed by {self._name}"
"""

MODULE_WITH_ASYNC_EXCEPTION_MIX = """
class TimeoutError(Exception):
    pass

async def fetch(url):
    return f"fetched {url}"

def validate(x):
    return x > 0
"""


def test_exception_class_not_wrapped(create_module, calls, sync_wrapper_factory):
    """Exception classes must NOT be wrapped — try/except must still work."""
    config = create_module(MODULE_WITH_EXCEPTION)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service, ServiceError  # noqa: PLC0415

    # Exception class should work normally in try/except
    try:
        raise ServiceError("test error")  # noqa: EM101, TRY003, TRY301
    except ServiceError:
        pass  # should catch without issues

    # But Service methods should be wrapped
    Service().process()
    assert calls == ["w_before", "w_after"]


def test_nested_exception_class_not_wrapped(create_module, calls, sync_wrapper_factory):
    """Exception classes nested inside a class must NOT be wrapped."""
    config = create_module(MODULE_WITH_NESTED_EXCEPTION)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service  # noqa: PLC0415

    # Nested exception should work normally
    try:
        raise Service.NotFoundError("not found")  # noqa: EM101, TRY003, TRY301
    except Service.NotFoundError:
        pass  # should catch without issues

    # But Service.get should be wrapped
    Service().get(42)
    assert calls == ["w_before", "w_after"]


def test_base_exception_subclass_not_wrapped(create_module, calls, sync_wrapper_factory):
    """BaseException subclasses must NOT be wrapped."""
    config = create_module(MODULE_WITH_BASE_EXCEPTION)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import FatalError, Service  # noqa: PLC0415

    try:
        raise FatalError("fatal")  # noqa: EM101, TRY301
    except FatalError:
        pass

    Service().run()
    assert calls == ["w_before", "w_after"]


def test_dunders_and_properties_not_wrapped(create_module, calls, sync_wrapper_factory):
    """Dunder methods and properties must NOT be wrapped, but normal methods should."""
    config = create_module(MODULE_WITH_DUNDERS_AND_PROPERTIES)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service  # noqa: PLC0415

    svc = Service("test")

    # __str__ should work without wrapper calls
    str(svc)
    assert calls == []

    # __repr__ should work without wrapper calls
    repr(svc)
    assert calls == []

    # property should work without wrapper calls
    assert svc.name == "test"
    assert calls == []

    # But process() should be wrapped
    svc.process()
    assert calls == ["w_before", "w_after"]


def test_exception_with_async_functions_coexist(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory
):
    """Exception classes skipped while sync/async functions in same module are wrapped."""
    config = create_module(MODULE_WITH_ASYNC_EXCEPTION_MIX)

    Wrapper.wrap_all(
        (sync_wrapper_factory("s"), async_wrapper_factory("a")),
        config=config,
    )

    from myapp.service import TimeoutError as SvcTimeout  # noqa: PLC0415
    from myapp.service import fetch, validate  # noqa: PLC0415

    # Exception should work
    try:
        raise SvcTimeout("timed out")  # noqa: EM101, TRY003, TRY301
    except SvcTimeout:
        pass

    assert calls == []

    # Sync function wrapped
    validate(1)
    assert calls == ["s_before", "s_after"]

    # Async function wrapped
    calls.clear()
    asyncio.run(fetch("https://x.com"))
    assert calls == ["a_before", "a_after"]
