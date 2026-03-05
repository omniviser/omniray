"""Type aliases."""

from collections.abc import Callable
from typing import Any

type ModuleAttr = Any  # Function, class, or variable from module namespace
type WraptInstance = Any  # None (function/static), class (classmethod), or object (method)
type CallResult = Any  # Return value from wrapped function call

type WrapperPair = tuple[Callable[..., Any] | None, Callable[..., Any] | None]  # (sync, async) pair
type WrapperSpec = WrapperPair | Callable[..., Any]  # Tuple pair or single callable for both
