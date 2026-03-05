"""E2E tests for skip_wrap — named functions/methods must NOT be wrapped."""

import asyncio

from omniwrap.config import DiscoveryConfig
from omniwrap.wrapper import Wrapper

MODULE_WITH_EXCLUDED_METHOD = """
class Conversation:
    def to_pydantic(self):
        return {"type": "conversation"}

    def process(self):
        return "done"

class Message:
    def to_pydantic(self):
        return {"type": "message"}

    def send(self):
        return "sent"
"""

MODULE_WITH_EXCLUDED_METHODS_MULTIPLE = """
class Model:
    def to_pydantic(self):
        return {}

    def to_dict(self):
        return {}

    def save(self):
        return "saved"
"""


def test_skip_wrap_skips_named_methods(create_module, calls, sync_wrapper_factory):
    """Methods in skip_wrap must NOT be wrapped, other methods must be."""
    config = create_module(MODULE_WITH_EXCLUDED_METHOD)
    config = DiscoveryConfig(
        paths=config.paths, exclude=config.exclude, skip_wrap=frozenset({"to_pydantic"})
    )

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Conversation, Message  # noqa: PLC0415

    conv = Conversation()
    msg = Message()

    conv.to_pydantic()
    assert calls == []

    msg.to_pydantic()
    assert calls == []

    conv.process()
    assert calls == ["w_before", "w_after"]

    calls.clear()
    msg.send()
    assert calls == ["w_before", "w_after"]


def test_skip_wrap_multiple_names(create_module, calls, sync_wrapper_factory):
    """Multiple method names can be excluded at once."""
    config = create_module(MODULE_WITH_EXCLUDED_METHODS_MULTIPLE)
    config = DiscoveryConfig(
        paths=config.paths,
        exclude=config.exclude,
        skip_wrap=frozenset({"to_pydantic", "to_dict"}),
    )

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Model  # noqa: PLC0415

    m = Model()

    m.to_pydantic()
    assert calls == []

    m.to_dict()
    assert calls == []

    m.save()
    assert calls == ["w_before", "w_after"]


def test_empty_skip_wrap_wraps_everything(create_module, calls, sync_wrapper_factory):
    """Empty skip_wrap should wrap all methods normally."""
    config = create_module(MODULE_WITH_EXCLUDED_METHOD)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import Conversation  # noqa: PLC0415

    conv = Conversation()

    conv.to_pydantic()
    assert calls == ["w_before", "w_after"]

    calls.clear()
    conv.process()
    assert calls == ["w_before", "w_after"]


MODULE_WITH_DESCRIPTORS_AND_ASYNC = """
class Service:
    @classmethod
    def from_config(cls):
        return cls()

    @staticmethod
    def validate():
        return True

    async def fetch(self):
        return "data"

    def process(self):
        return "done"
"""

MODULE_WITH_EXCLUDED_FUNCTION = """
def healthcheck():
    return "ok"

def process():
    return "done"
"""


def test_skip_wrap_works_with_classmethod_staticmethod_async(
    create_module, calls, sync_wrapper_factory, async_wrapper_factory
):
    """skip_wrap must work with @classmethod, @staticmethod, and async methods."""
    config = create_module(MODULE_WITH_DESCRIPTORS_AND_ASYNC)
    config = DiscoveryConfig(
        paths=config.paths,
        exclude=config.exclude,
        skip_wrap=frozenset({"from_config", "validate", "fetch"}),
    )

    Wrapper.wrap_all((sync_wrapper_factory("w"), async_wrapper_factory("a")), config=config)

    from myapp.service import Service  # noqa: PLC0415

    Service.from_config()
    assert calls == []

    Service.validate()
    assert calls == []

    asyncio.run(Service().fetch())
    assert calls == []

    Service().process()
    assert calls == ["w_before", "w_after"]


def test_skip_wrap_works_with_module_level_functions(create_module, calls, sync_wrapper_factory):
    """skip_wrap must also exclude module-level functions, not just class methods."""
    config = create_module(MODULE_WITH_EXCLUDED_FUNCTION)
    config = DiscoveryConfig(
        paths=config.paths,
        exclude=config.exclude,
        skip_wrap=frozenset({"healthcheck"}),
    )

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import healthcheck, process  # noqa: PLC0415

    healthcheck()
    assert calls == []

    process()
    assert calls == ["w_before", "w_after"]
