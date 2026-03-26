"""E2E tests for the full omniwrap pipeline — single wrapper scenarios."""

import asyncio

from omniwrap.wrapper import Wrapper


def test_sync_function_wrapping(create_module, sync_source):
    """E2E: config → discovery → wrap sync function → verify wrapper called."""
    config = create_module(sync_source)

    calls = []

    def sync_wrapper(wrapped, _instance, args, kwargs):
        calls.append(("sync", wrapped.__name__, args))
        return wrapped(*args, **kwargs)

    Wrapper.wrap_all(sync_wrapper, config=config, enabled=True)

    from myapp.service import greet  # noqa: PLC0415

    result = greet("World")

    assert result == "Hello World"
    assert calls == [("sync", "greet", ("World",))]


def test_async_function_wrapping(create_module, async_source):
    """E2E: config → discovery → wrap async function → verify wrapper called."""
    config = create_module(async_source)

    calls = []

    def sync_wrapper(wrapped, _instance, args, kwargs):
        calls.append(("sync", wrapped.__name__, args))
        return wrapped(*args, **kwargs)

    async def async_wrapper(wrapped, _instance, args, kwargs):
        calls.append(("async", wrapped.__name__, args))
        return await wrapped(*args, **kwargs)

    Wrapper.wrap_all((sync_wrapper, async_wrapper), config=config, enabled=True)

    from myapp.service import fetch  # noqa: PLC0415

    result = asyncio.run(fetch("https://example.com"))

    assert result == "Fetched https://example.com"
    assert calls == [("async", "fetch", ("https://example.com",))]


def test_multi_module_wrapping(create_modules, calls, sync_wrapper_factory, sync_source):
    """E2E: wrap_all discovers and wraps functions from multiple modules."""
    config = create_modules(
        {
            "myapp/service.py": sync_source,
            "myapp/utils.py": 'def helper(x):\n    return f"helped {x}"',
        }
    )

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import greet  # noqa: PLC0415
    from myapp.utils import helper  # noqa: PLC0415

    greet("World")
    assert calls == ["w_before", "w_after"]

    calls.clear()
    helper("test")
    assert calls == ["w_before", "w_after"]


def test_multi_module_mixed_sync_async(
    create_modules, calls, sync_wrapper_factory, async_wrapper_factory, sync_source, async_source
):
    """E2E: wrap_all handles sync and async across multiple modules."""
    config = create_modules(
        {
            "myapp/service.py": sync_source,
            "myapp/utils.py": async_source,
        }
    )

    Wrapper.wrap_all(
        (sync_wrapper_factory("s"), async_wrapper_factory("a")),
        config=config,
    )

    from myapp.service import greet  # noqa: PLC0415
    from myapp.utils import fetch  # noqa: PLC0415

    greet("World")
    assert calls == ["s_before", "s_after"]

    calls.clear()
    asyncio.run(fetch("https://x.com"))
    assert calls == ["a_before", "a_after"]
