"""Wrapper logic for applying decorators.

This module provides the Wrapper class which applies a decorator to functions, methods, and classes
across the application using the wrapt library for safe monkey patching.
"""

import inspect
import logging
from collections.abc import Callable
from os import getenv
from types import ModuleType

import wrapt

from omniwrap.config import DiscoveryConfig
from omniwrap.discovery import ModuleDiscovery
from omniwrap.types import ModuleAttr, WrapperPair, WrapperSpec

logger = logging.getLogger(__name__)


class Wrapper:
    """Applies a decorator to functions, methods, and classes using wrapt."""

    @classmethod
    def wrap_all(
        cls,
        *wrappers: WrapperSpec,
        config: DiscoveryConfig | None = None,
        enabled: bool | None = True,
    ) -> None:
        """Main entry point: Wrap all modules in the application.

        Wrappers are applied in order — first wrapper is innermost (closest to the
        original function).

        Args:
            *wrappers: One or more wrappers. Each can be a single callable (used for
                both sync and async) or a tuple of (sync_wrapper, async_wrapper).
                Use None in a tuple to skip sync or async wrapping.
            config: Optional discovery config (None = load from pyproject.toml)
            enabled: Enable wrapping (True), disable (False), or read from env var (None)
        """
        if not cls._should_wrap(enabled=enabled):
            return
        if config is None:
            config = DiscoveryConfig.from_pyproject()
        normalized = cls._normalize_wrappers(wrappers)
        discovered = ModuleDiscovery.discover(config)
        for module in discovered:
            cls._wrap_module(module, normalized, skip_wrap=config.skip_wrap)

    @classmethod
    def _normalize_wrappers(cls, wrappers: tuple[WrapperSpec, ...]) -> list[WrapperPair]:
        """Convert wrapper specs to normalized (sync, async) pairs."""
        return [spec if isinstance(spec, tuple) else (spec, spec) for spec in wrappers]

    @classmethod
    def _should_wrap(cls, *, enabled: bool | None) -> bool:
        """Determine if wrapping should be enabled.

        Args:
            enabled: True (always wrap), False (never wrap), None (read from env var)
        """
        if enabled is None:
            return getenv("OMNIWRAP", "false").lower() in ("true", "1", "yes")
        return enabled

    @classmethod
    def _wrap_module(
        cls,
        module: ModuleType,
        wrappers: list[WrapperPair],
        *,
        skip_wrap: frozenset[str] = frozenset(),
    ) -> None:
        """Wrap all functions and classes in a module."""
        attrs = cls._get_module_attrs(module)
        if attrs is None:
            return
        for name, obj in attrs:
            if not cls._is_defined_in_module(obj, module.__name__):
                continue
            cls._wrap_object(module, name, obj, wrappers, skip_wrap=skip_wrap)

    @classmethod
    def _get_module_attrs(cls, module: ModuleType) -> list[tuple[str, ModuleAttr]] | None:
        """Get top-level module attributes (functions, classes, variables)."""
        try:
            return inspect.getmembers(module)
        except TypeError:
            return None

    @classmethod
    def _wrap_object(
        cls,
        module: ModuleType,
        name: str,
        obj: ModuleAttr,
        wrappers: list[WrapperPair],
        *,
        skip_wrap: frozenset[str] = frozenset(),
    ) -> None:
        """Wrap a single object (function or class)."""
        if getattr(obj, "_omniwrap_skip", False) or name in skip_wrap:
            return  # marked with @skip_wrap or excluded by config
        if inspect.isclass(obj):
            if issubclass(obj, BaseException):
                return  # Never wrap exception classes - breaks Python's exception handling
            cls._wrap_class(obj, wrappers, skip_wrap=skip_wrap)
        elif callable(obj) and not isinstance(obj, wrapt.FunctionWrapper):
            for wrapper_pair in wrappers:
                cls._wrap_callable(module, name, wrapper_pair)

    @classmethod
    def _wrap_class(
        cls,
        cls_obj: type,
        wrappers: list[WrapperPair],
        *,
        skip_wrap: frozenset[str] = frozenset(),
    ) -> None:
        """Wrap all methods in a class using wrapt."""
        for attr_name, static_attr in vars(cls_obj).items():
            if cls._should_skip_attr(attr_name, static_attr, skip_wrap=skip_wrap):
                continue
            for wrapper_pair in wrappers:
                cls._wrap_callable(cls_obj, attr_name, wrapper_pair)

    @classmethod
    def _should_skip_attr(
        cls,
        attr_name: str,
        static_attr: object,
        *,
        skip_wrap: frozenset[str] = frozenset(),
    ) -> bool:
        """Check if attribute should be skipped from wrapping."""
        is_excluded = attr_name in skip_wrap
        is_dunder = attr_name.startswith("__") and attr_name.endswith("__")
        if is_excluded or is_dunder:
            return True
        if isinstance(static_attr, property):
            return True  # properties can't be wrapped
        # Skip nested exception classes - wrapping them breaks Python's exception handling
        if isinstance(static_attr, type) and issubclass(static_attr, BaseException):
            return True
        # Get underlying function for classmethod/staticmethod
        func = getattr(static_attr, "__func__", static_attr)
        if not callable(func) or getattr(func, "_omniwrap_skip", False):
            return True  # not a method or marked with @skip_wrap
        # classmethod/staticmethod descriptors have __wrapped__ since Python 3.10
        # pointing to the original function — not a wrapt wrapper, don't skip.
        # Use type() instead of isinstance() because wrapt's FunctionWrapper proxies
        # isinstance checks and would match (classmethod, staticmethod) too.
        if type(static_attr) in (classmethod, staticmethod):
            return False
        return isinstance(static_attr, wrapt.FunctionWrapper)  # already wrapped by omniwrap

    @classmethod
    def _get_underlying_func(cls, parent: ModuleType | type, name: str) -> Callable:
        """Extract the underlying function from a classmethod/staticmethod/function."""
        static_attr = inspect.getattr_static(parent, name)
        return getattr(static_attr, "__func__", static_attr)

    @classmethod
    def _wrap_callable(cls, parent: ModuleType | type, name: str, wrappers: WrapperPair) -> None:
        """Wrap a single callable (function or method)."""
        try:
            sync_wrapper, async_wrapper = wrappers
            func = cls._get_underlying_func(parent, name)
            wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
            if wrapper is None:
                return
            wrapt.wrap_function_wrapper(parent, name, wrapper)
            parent_name = parent.__name__ if hasattr(parent, "__name__") else str(parent)
            logger.debug("Wrapped: %s.%s", parent_name, name)
        except (TypeError, AttributeError) as exc:
            parent_name = parent.__name__ if hasattr(parent, "__name__") else str(parent)
            logger.debug("Skipped wrapping %s.%s: %s", parent_name, name, exc)

    @classmethod
    def _is_defined_in_module(cls, obj: ModuleAttr, module_name: str) -> bool:
        """Check if an object is defined in the specified module."""
        return hasattr(obj, "__module__") and obj.__module__ == module_name
