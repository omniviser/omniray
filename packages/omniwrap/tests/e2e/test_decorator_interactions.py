"""E2E tests for decorator interactions — how omniwrap behaves with real-world decorators.

These tests verify that omniwrap correctly wraps functions decorated with stdlib
decorators like ``@functools.lru_cache``, ``@functools.wraps``, ``@dataclass``,
etc. The idempotency guard uses ``isinstance(obj, wrapt.FunctionWrapper)`` to
only skip functions already wrapped by omniwrap itself — not by other decorators.
"""

import asyncio

from omniwrap.wrapper import Wrapper

MODULE_LRU_CACHE = """
from functools import lru_cache

@lru_cache(maxsize=32)
def expensive(x):
    return x * 2

def regular(x):
    return x + 1
"""

MODULE_LRU_CACHE_METHOD = """
from functools import lru_cache

class Service:
    @lru_cache(maxsize=32)
    def compute(self, x):
        return x * 2

    def process(self, x):
        return x + 1
"""

MODULE_FUNCTOOLS_WRAPS = """
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def decorated(x):
    return x * 3

def plain(x):
    return x + 1
"""

MODULE_CUSTOM_DECORATOR_NO_WRAPS = """
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def decorated(x):
    return x * 3

def plain(x):
    return x + 1
"""

MODULE_DATACLASS = """
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

    def greet(self):
        return f"Hi, I'm {self.name}"

    def is_adult(self):
        return self.age >= 18
"""

MODULE_CACHED_PROPERTY = """
from functools import cached_property

class Config:
    def __init__(self, raw):
        self._raw = raw

    @cached_property
    def parsed(self):
        return self._raw.upper()

    def get_raw(self):
        return self._raw
"""

MODULE_ABC = """
from abc import ABC, abstractmethod

class BaseService(ABC):
    @abstractmethod
    def process(self, x):
        ...

class ConcreteService(BaseService):
    def process(self, x):
        return f"processed {x}"

    def extra(self):
        return "extra"
"""

MODULE_STACKED_DECORATORS = """
from functools import wraps

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def validate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def no_wraps_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@log_call
@validate
def stacked_with_wraps(x):
    return x * 2

@no_wraps_decorator
def stacked_no_wraps(x):
    return x * 3

def plain(x):
    return x + 1
"""

MODULE_ASYNC_DECORATED = """
from functools import wraps

def async_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper

@async_decorator
async def decorated_fetch(url):
    return f"fetched {url}"

async def plain_fetch(url):
    return f"plain {url}"
"""

MODULE_MIXED_CLASS_DECORATORS = """
from functools import cached_property, lru_cache

class Service:
    def __init__(self, name):
        self._name = name

    @cached_property
    def label(self):
        return self._name.upper()

    @lru_cache(maxsize=16)
    def compute(self, x):
        return x * 2

    @staticmethod
    def validate(x):
        return x > 0

    @classmethod
    def create(cls, name):
        return cls(name)

    def process(self, x):
        return f"{self._name}: {x}"
"""


# --- @functools.lru_cache ---


def test_lru_cache_function_wrapped(create_module, calls, sync_wrapper_factory):
    """Module-level @lru_cache function IS wrapped (omniwrap sees through it)."""
    config = create_module(MODULE_LRU_CACHE)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import expensive, regular  # noqa: PLC0415

    regular(1)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    expensive(2)
    assert calls == ["w_before", "w_after"]


def test_lru_cache_method_wrapped(create_module, calls, sync_wrapper_factory):
    """Class method with @lru_cache IS wrapped."""
    config = create_module(MODULE_LRU_CACHE_METHOD)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service  # noqa: PLC0415

    svc = Service()

    svc.process(1)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    svc.compute(2)
    assert calls == ["w_before", "w_after"]


# --- @functools.wraps ---


def test_functools_wraps_decorator_wrapped(create_module, calls, sync_wrapper_factory):
    """Function decorated with @functools.wraps-based decorator IS wrapped."""
    config = create_module(MODULE_FUNCTOOLS_WRAPS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import decorated, plain  # noqa: PLC0415

    plain(1)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    decorated(2)
    assert calls == ["w_before", "w_after"]


def test_custom_decorator_without_wraps_is_wrapped(create_module, calls, sync_wrapper_factory):
    """Function with custom decorator (no @wraps) IS wrapped."""
    config = create_module(MODULE_CUSTOM_DECORATOR_NO_WRAPS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import decorated, plain  # noqa: PLC0415

    plain(1)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    decorated(2)
    assert calls == ["w_before", "w_after"]


# --- @dataclass ---


def test_dataclass_methods_wrapped(create_module, calls, sync_wrapper_factory):
    """@dataclass custom methods are wrapped, generated dunders are skipped."""
    config = create_module(MODULE_DATACLASS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import User  # noqa: PLC0415

    user = User(name="Alice", age=30)

    # Custom methods ARE wrapped
    user.greet()
    assert calls == ["w_before", "w_after"]

    calls.clear()
    user.is_adult()
    assert calls == ["w_before", "w_after"]

    # Generated __init__, __repr__, __eq__ are dunders — not wrapped
    calls.clear()
    User(name="Bob", age=25)
    assert calls == []

    calls.clear()
    repr(user)
    assert calls == []


# --- @cached_property ---


def test_cached_property_skipped(create_module, calls, sync_wrapper_factory):
    """@cached_property is skipped (not callable), but regular methods are wrapped."""
    config = create_module(MODULE_CACHED_PROPERTY)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Config  # noqa: PLC0415

    cfg = Config("hello")

    cfg.get_raw()
    assert calls == ["w_before", "w_after"]

    # cached_property access should work without wrapper interference
    calls.clear()
    assert cfg.parsed == "HELLO"
    assert calls == []


# --- ABC + @abstractmethod ---


def test_abstract_method_on_concrete_class_wrapped(create_module, calls, sync_wrapper_factory):
    """Concrete implementations of @abstractmethod ARE wrapped."""
    config = create_module(MODULE_ABC)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import ConcreteService  # noqa: PLC0415

    svc = ConcreteService()
    svc.process("x")
    assert calls == ["w_before", "w_after"]

    calls.clear()
    svc.extra()
    assert calls == ["w_before", "w_after"]


# --- Stacked decorators ---


def test_stacked_wraps_decorators_wrapped(create_module, calls, sync_wrapper_factory):
    """All decorated functions are wrapped regardless of @wraps usage."""
    config = create_module(MODULE_STACKED_DECORATORS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import plain, stacked_no_wraps, stacked_with_wraps  # noqa: PLC0415

    plain(1)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    stacked_with_wraps(2)
    assert calls == ["w_before", "w_after"]

    calls.clear()
    stacked_no_wraps(3)
    assert calls == ["w_before", "w_after"]


# --- Async decorated ---


def test_async_wraps_decorator_wrapped(create_module, calls, async_wrapper_factory):
    """Async function with @wraps-based decorator IS wrapped."""
    config = create_module(MODULE_ASYNC_DECORATED)

    Wrapper.wrap_all(async_wrapper_factory("w"), config=config)

    from myapp.service import decorated_fetch, plain_fetch  # noqa: PLC0415

    asyncio.run(plain_fetch("https://x.com"))
    assert calls == ["w_before", "w_after"]

    calls.clear()
    asyncio.run(decorated_fetch("https://x.com"))
    assert calls == ["w_before", "w_after"]


# --- Mixed class decorators ---


def test_mixed_class_decorators(create_module, calls, sync_wrapper_factory):
    """Class with cached_property + lru_cache + staticmethod + classmethod + regular."""
    config = create_module(MODULE_MIXED_CLASS_DECORATORS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Service  # noqa: PLC0415

    svc = Service("test")

    # regular method → wrapped
    svc.process("x")
    assert calls == ["w_before", "w_after"]

    # @staticmethod → wrapped
    calls.clear()
    Service.validate(1)
    assert calls == ["w_before", "w_after"]

    # @classmethod → wrapped
    calls.clear()
    Service.create("new")
    assert calls == ["w_before", "w_after"]

    # @cached_property → skipped (not callable)
    calls.clear()
    assert svc.label == "TEST"
    assert calls == []

    # @lru_cache method → NOW wrapped (isinstance check, not __wrapped__)
    calls.clear()
    svc.compute(5)
    assert calls == ["w_before", "w_after"]
