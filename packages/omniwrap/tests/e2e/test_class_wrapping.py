"""E2E tests for wrapping class methods with multiple wrappers."""

import asyncio

import pytest
from omniwrap.wrapper import Wrapper

CLASS_SOURCE = """
class UserService:
    def get_user(self, user_id):
        return f"User {user_id}"

    async def fetch_user(self, user_id):
        return f"Fetched user {user_id}"

    @classmethod
    def create(cls, name):
        return f"Created {name}"

    @staticmethod
    def validate(user_id):
        return user_id > 0
"""

MIXED_MODULE_SOURCE = """
def greet(name):
    return f"Hello {name}"

class Calculator:
    def add(self, a, b):
        return a + b

    @staticmethod
    def multiply(a, b):
        return a * b
"""


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
def test_multiple_wrappers_on_instance_method(
    create_module, calls, sync_wrapper_factory, wrapper_count, expected_order
):
    """Multiple wrappers applied in order on instance methods."""
    config = create_module(CLASS_SOURCE)
    labels = ["a", "b", "c"][:wrapper_count]
    wrappers = [sync_wrapper_factory(label) for label in labels]

    Wrapper.wrap_all(*wrappers, config=config)

    from myapp.service import UserService  # noqa: PLC0415

    svc = UserService()
    result = svc.get_user(42)

    assert result == "User 42"
    assert calls == expected_order


def test_multiple_wrappers_on_async_method(create_module, calls, async_wrapper_factory):
    """Multiple wrappers applied in order on async instance methods."""
    config = create_module(CLASS_SOURCE)

    Wrapper.wrap_all(
        async_wrapper_factory("a"),
        async_wrapper_factory("b"),
        config=config,
    )

    from myapp.service import UserService  # noqa: PLC0415

    svc = UserService()
    result = asyncio.run(svc.fetch_user(42))

    assert result == "Fetched user 42"
    assert calls == ["b_before", "a_before", "a_after", "b_after"]


def test_multiple_wrappers_on_classmethod(create_module, calls, sync_wrapper_factory):
    """Multiple wrappers applied in order on classmethods."""
    config = create_module(CLASS_SOURCE)

    Wrapper.wrap_all(
        sync_wrapper_factory("a"),
        sync_wrapper_factory("b"),
        config=config,
    )

    from myapp.service import UserService  # noqa: PLC0415

    result = UserService.create("Alice")

    assert result == "Created Alice"
    assert calls == ["b_before", "a_before", "a_after", "b_after"]


def test_multiple_wrappers_on_staticmethod(create_module, calls, sync_wrapper_factory):
    """Multiple wrappers applied in order on staticmethods."""
    config = create_module(CLASS_SOURCE)

    Wrapper.wrap_all(
        sync_wrapper_factory("a"),
        sync_wrapper_factory("b"),
        config=config,
    )

    from myapp.service import UserService  # noqa: PLC0415

    result = UserService.validate(42)

    assert result is True
    assert calls == ["b_before", "a_before", "a_after", "b_after"]


def test_tuple_wrappers_dispatch_sync_async_methods(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory
):
    """Tuple wrappers correctly dispatch sync/async on class methods."""
    config = create_module(CLASS_SOURCE)

    Wrapper.wrap_all(
        (sync_wrapper_factory("s"), async_wrapper_factory("a")),
        config=config,
    )

    from myapp.service import UserService  # noqa: PLC0415

    svc = UserService()

    svc.get_user(1)
    assert calls == ["s_before", "s_after"]

    calls.clear()
    asyncio.run(svc.fetch_user(1))
    assert calls == ["a_before", "a_after"]


def test_mixed_functions_and_classes_wrapped(create_module, calls, sync_wrapper_factory):
    """Module with both functions and classes — all get wrapped."""
    config = create_module(MIXED_MODULE_SOURCE)

    Wrapper.wrap_all(
        sync_wrapper_factory("a"),
        sync_wrapper_factory("b"),
        config=config,
    )

    from myapp.service import Calculator, greet  # noqa: PLC0415

    greet("World")
    assert calls == ["b_before", "a_before", "a_after", "b_after"]

    calls.clear()
    calc = Calculator()
    assert calc.add(2, 3) == 5
    assert calls == ["b_before", "a_before", "a_after", "b_after"]

    calls.clear()
    assert Calculator.multiply(4, 5) == 20
    assert calls == ["b_before", "a_before", "a_after", "b_after"]


def test_classes_in_multiple_modules_wrapped(create_modules, calls, sync_wrapper_factory):
    """Classes across multiple modules all get wrapped."""
    config = create_modules(
        {
            "myapp/service.py": CLASS_SOURCE,
            "myapp/utils.py": MIXED_MODULE_SOURCE,
        }
    )

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import UserService  # noqa: PLC0415
    from myapp.utils import Calculator, greet  # noqa: PLC0415

    UserService().get_user(1)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    Calculator().add(2, 3)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    greet("World")
    assert calls == ["w_before", "w_after"]
