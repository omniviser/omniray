"""Tests for Wrapper._get_module_attrs() method."""

import inspect
from types import ModuleType

from omniwrap.wrapper import Wrapper


def test_returns_members_for_normal_module():
    """Should return inspect.getmembers() for normal modules."""
    module = ModuleType("test_module")
    module.some_func = lambda: None

    result = Wrapper._get_module_attrs(module)

    assert result is not None
    assert isinstance(result, list)
    names = [name for name, _ in result]
    assert "some_func" in names


def test_returns_none_on_typeerror(mocker):
    """Should return None when inspect.getmembers raises TypeError."""
    mocker.patch.object(inspect, "getmembers", side_effect=TypeError("cannot inspect"))

    module = ModuleType("problematic_module")

    result = Wrapper._get_module_attrs(module)

    assert result is None
