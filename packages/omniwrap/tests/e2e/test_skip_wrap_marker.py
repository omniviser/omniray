"""E2E tests for @skip_wrap — marked functions, methods, and classes must NOT be wrapped."""

import asyncio

from omniwrap.wrapper import Wrapper

MODULE_WITH_SKIP_WRAP_SYNC = """
from omniwrap import skip_wrap

@skip_wrap
def healthcheck():
    return "ok"

def process():
    return "done"
"""

MODULE_WITH_SKIP_WRAP_ASYNC = """
from omniwrap import skip_wrap

@skip_wrap
async def healthcheck():
    return "ok"

async def fetch(url):
    return f"fetched {url}"
"""

MODULE_WITH_SKIP_WRAP_METHOD = """
from omniwrap import skip_wrap

class Service:
    @skip_wrap
    def healthcheck(self):
        return "ok"

    def process(self):
        return "done"
"""

MODULE_WITH_SKIP_WRAP_CLASS = """
from omniwrap import skip_wrap

@skip_wrap
class Internal:
    def helper(self):
        return "internal"

class Public:
    def api(self):
        return "public"
"""

MODULE_WITH_SKIP_WRAP_MIXED = """
from omniwrap import skip_wrap

class ServiceError(Exception):
    pass

@skip_wrap
def healthcheck():
    return "ok"

class Service:
    def __init__(self):
        self._state = "ready"

    @skip_wrap
    def internal_tick(self):
        return "tick"

    def process(self):
        return "done"
"""


def test_skip_wrap_on_sync_function(create_module, calls, sync_wrapper_factory):
    """@skip_wrap sync function must NOT be wrapped, sibling function must be."""
    config = create_module(MODULE_WITH_SKIP_WRAP_SYNC)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import healthcheck, process  # noqa: PLC0415

    healthcheck()
    assert calls == []

    process()
    assert calls == ["w_before", "w_after"]


def test_skip_wrap_on_async_function(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory
):
    """@skip_wrap async function must NOT be wrapped."""
    config = create_module(MODULE_WITH_SKIP_WRAP_ASYNC)

    Wrapper.wrap_all(
        (sync_wrapper_factory("s"), async_wrapper_factory("a")),
        config=config,
    )

    from myapp.service import fetch, healthcheck  # noqa: PLC0415

    asyncio.run(healthcheck())
    assert calls == []

    asyncio.run(fetch("https://x.com"))
    assert calls == ["a_before", "a_after"]


def test_skip_wrap_on_method(create_module, calls, sync_wrapper_factory):
    """@skip_wrap method must NOT be wrapped, other methods in same class must be."""
    config = create_module(MODULE_WITH_SKIP_WRAP_METHOD)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service  # noqa: PLC0415

    svc = Service()

    svc.healthcheck()
    assert calls == []

    svc.process()
    assert calls == ["w_before", "w_after"]


def test_skip_wrap_on_class(create_module, calls, sync_wrapper_factory):
    """@skip_wrap on entire class — no methods wrapped. Sibling class IS wrapped."""
    config = create_module(MODULE_WITH_SKIP_WRAP_CLASS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Internal, Public  # noqa: PLC0415

    Internal().helper()
    assert calls == []

    Public().api()
    assert calls == ["w_before", "w_after"]


def test_skip_wrap_mixed_with_exceptions_and_dunders(create_module, calls, sync_wrapper_factory):
    """@skip_wrap + exceptions + dunders all coexist correctly."""
    config = create_module(MODULE_WITH_SKIP_WRAP_MIXED)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service, ServiceError, healthcheck  # noqa: PLC0415

    # Exception class works normally
    try:
        raise ServiceError("err")  # noqa: EM101, TRY301
    except ServiceError:
        pass

    assert calls == []

    # skip_wrap function not wrapped
    healthcheck()
    assert calls == []

    svc = Service()

    # dunder not wrapped
    str(svc)
    assert calls == []

    # skip_wrap method not wrapped
    svc.internal_tick()
    assert calls == []

    # regular method IS wrapped
    svc.process()
    assert calls == ["w_before", "w_after"]
