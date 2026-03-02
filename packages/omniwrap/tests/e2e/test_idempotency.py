"""E2E tests for wrap_all() idempotency — calling wrap_all multiple times."""

import asyncio

import pytest
from omniwrap.wrapper import Wrapper
from tests.e2e.conftest import ASYNC_SOURCE, SYNC_SOURCE

CLASS_SOURCE = """
class Service:
    def process(self, x):
        return f"processed {x}"

    @classmethod
    def create(cls, name):
        return f"created {name}"

    @staticmethod
    def validate(x):
        return x > 0

    async def fetch(self, url):
        return f"fetched {url}"
"""


def test_duplicate_wrap_all_does_not_double_wrap_sync(create_module, calls, sync_wrapper_factory):
    """Calling wrap_all() twice with the same wrapper should NOT double-wrap."""
    config = create_module(SYNC_SOURCE)
    wrapper = sync_wrapper_factory("w")

    Wrapper.wrap_all(wrapper, config=config)
    Wrapper.wrap_all(wrapper, config=config)

    from myapp.service import greet  # noqa: PLC0415

    greet("World")

    assert calls == ["w_before", "w_after"]


def test_duplicate_wrap_all_does_not_double_wrap_async(create_module, calls, async_wrapper_factory):
    """Calling wrap_all() twice should NOT double-wrap async functions."""
    config = create_module(ASYNC_SOURCE)
    wrapper = async_wrapper_factory("w")

    Wrapper.wrap_all(wrapper, config=config)
    Wrapper.wrap_all(wrapper, config=config)

    from myapp.service import fetch  # noqa: PLC0415

    asyncio.run(fetch("https://x.com"))

    assert calls == ["w_before", "w_after"]


def test_different_wrap_all_calls_do_not_stack(create_module, calls, sync_wrapper_factory):
    """Two separate wrap_all() calls with different wrappers — second is ignored."""
    config = create_module(SYNC_SOURCE)

    Wrapper.wrap_all(sync_wrapper_factory("first"), config=config)
    Wrapper.wrap_all(sync_wrapper_factory("second"), config=config)

    from myapp.service import greet  # noqa: PLC0415

    greet("World")

    assert calls == ["first_before", "first_after"]


@pytest.mark.parametrize(
    "wrapper_count",
    [
        pytest.param(2, id="2-wrappers"),
        pytest.param(3, id="3-wrappers"),
    ],
)
def test_single_call_with_multiple_wrappers_then_duplicate_call(
    create_module, calls, sync_wrapper_factory, wrapper_count
):
    """wrap_all(w1, w2) then wrap_all(w3) — w3 should be ignored."""
    config = create_module(SYNC_SOURCE)
    labels = ["a", "b", "c"][:wrapper_count]
    wrappers = [sync_wrapper_factory(label) for label in labels]

    Wrapper.wrap_all(*wrappers, config=config)
    Wrapper.wrap_all(sync_wrapper_factory("stray"), config=config)

    from myapp.service import greet  # noqa: PLC0415

    greet("World")

    assert "stray_before" not in calls
    assert "stray_after" not in calls


@pytest.mark.parametrize(
    "method_call",
    [
        pytest.param("instance", id="instance-method"),
        pytest.param("classmethod", id="classmethod"),
        pytest.param("staticmethod", id="staticmethod"),
        pytest.param("async", id="async-method"),
    ],
)
def test_duplicate_wrap_all_does_not_double_wrap_class_methods(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory, method_call
):
    """Calling wrap_all() twice should NOT double-wrap class methods."""
    config = create_module(CLASS_SOURCE)

    Wrapper.wrap_all(sync_wrapper_factory("first"), config=config)
    Wrapper.wrap_all(sync_wrapper_factory("second"), config=config)

    from myapp.service import Service  # noqa: PLC0415

    svc = Service()
    if method_call == "instance":
        svc.process("x")
    elif method_call == "classmethod":
        Service.create("x")
    elif method_call == "staticmethod":
        Service.validate(1)
    else:
        # async needs its own wrapper — but we're testing the guard here,
        # so we only care that second wrap_all is ignored
        calls.clear()
        config2 = create_module(CLASS_SOURCE)
        Wrapper.wrap_all(async_wrapper_factory("first"), config=config2)
        Wrapper.wrap_all(async_wrapper_factory("second"), config=config2)
        from myapp.service import Service as Svc2  # noqa: PLC0415

        asyncio.run(Svc2().fetch("https://x.com"))

    assert "second_before" not in calls
    assert "second_after" not in calls
