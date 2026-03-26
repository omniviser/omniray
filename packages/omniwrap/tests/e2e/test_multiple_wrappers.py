"""E2E tests for multiple wrappers — ordering, tuples, None, mixed specs."""

import asyncio

import pytest
from omniwrap.wrapper import Wrapper


@pytest.mark.parametrize(
    ("wrapper_count", "expected_order"),
    [
        pytest.param(
            2,
            ["b_before", "a_before", "a_after", "b_after"],
            id="2-wrappers",
        ),
        pytest.param(
            3,
            ["c_before", "b_before", "a_before", "a_after", "b_after", "c_after"],
            id="3-wrappers",
        ),
    ],
)
def test_sync_wrappers_ordering(
    create_module, calls, sync_wrapper_factory, wrapper_count, expected_order, sync_source
):
    """N sync wrappers applied in correct order (first = innermost)."""
    config = create_module(sync_source)
    labels = ["a", "b", "c"][:wrapper_count]
    wrappers = [sync_wrapper_factory(label) for label in labels]

    Wrapper.wrap_all(*wrappers, config=config)

    from myapp.service import greet  # noqa: PLC0415

    assert greet("World") == "Hello World"
    assert calls == expected_order


@pytest.mark.parametrize(
    ("wrapper_count", "expected_order"),
    [
        pytest.param(
            2,
            ["b_before", "a_before", "a_after", "b_after"],
            id="2-wrappers",
        ),
        pytest.param(
            3,
            ["c_before", "b_before", "a_before", "a_after", "b_after", "c_after"],
            id="3-wrappers",
        ),
    ],
)
def test_async_wrappers_ordering(
    create_module, calls, async_wrapper_factory, wrapper_count, expected_order, async_source
):
    """N async wrappers applied in correct order (first = innermost)."""
    config = create_module(async_source)
    labels = ["a", "b", "c"][:wrapper_count]
    wrappers = [async_wrapper_factory(label) for label in labels]

    Wrapper.wrap_all(*wrappers, config=config)

    from myapp.service import fetch  # noqa: PLC0415

    assert asyncio.run(fetch("https://x.com")) == "Fetched https://x.com"
    assert calls == expected_order


def test_tuple_wrappers_on_mixed_module(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory, mixed_source
):
    """Tuple (sync, async) wrappers correctly dispatch per function type."""
    config = create_module(mixed_source)

    Wrapper.wrap_all(
        (sync_wrapper_factory("sa"), async_wrapper_factory("aa")),
        (sync_wrapper_factory("sb"), async_wrapper_factory("ab")),
        config=config,
    )

    from myapp.service import fetch, greet  # noqa: PLC0415

    greet("World")
    assert calls == ["sb_before", "sa_before", "sa_after", "sb_after"]

    calls.clear()
    asyncio.run(fetch("https://x.com"))
    assert calls == ["ab_before", "aa_before", "aa_after", "ab_after"]


@pytest.mark.parametrize(
    ("wrapper_spec", "source_fixture", "is_async", "expected_calls"),
    [
        pytest.param(
            "none_sync",
            "async_source",
            True,
            ["a_before", "a_after"],
            id="None-sync-wraps-async-only",
        ),
        pytest.param(
            "none_async",
            "sync_source",
            False,
            ["a_before", "a_after"],
            id="None-async-wraps-sync-only",
        ),
        pytest.param(
            "none_sync",
            "sync_source",
            False,
            [],
            id="None-sync-skips-sync-function",
        ),
        pytest.param(
            "none_async",
            "async_source",
            True,
            [],
            id="None-async-skips-async-function",
        ),
    ],
)
def test_none_in_tuple_skips_wrapping(
    request,
    create_module,
    calls,
    sync_wrapper_factory,
    async_wrapper_factory,
    wrapper_spec,
    source_fixture,
    is_async,
    expected_calls,
):
    """None in a wrapper tuple skips wrapping for that function type."""
    source = request.getfixturevalue(source_fixture)
    config = create_module(source)

    if wrapper_spec == "none_sync":
        spec = (None, async_wrapper_factory("a"))
    else:
        spec = (sync_wrapper_factory("a"), None)

    Wrapper.wrap_all(spec, config=config)

    if is_async:
        from myapp.service import fetch  # noqa: PLC0415

        asyncio.run(fetch("https://x.com"))
    else:
        from myapp.service import greet  # noqa: PLC0415

        greet("World")

    assert calls == expected_calls


def test_mixed_single_and_tuple_wrappers(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory, sync_source
):
    """Mix of single callable and tuple wrappers in one wrap_all call."""
    config = create_module(sync_source)

    Wrapper.wrap_all(
        sync_wrapper_factory("single"),
        (sync_wrapper_factory("specific"), async_wrapper_factory("specific")),
        config=config,
    )

    from myapp.service import greet  # noqa: PLC0415

    greet("World")
    assert calls == [
        "specific_before",
        "single_before",
        "single_after",
        "specific_after",
    ]
