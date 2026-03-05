"""I/O logging and serialization of function arguments and results."""

import inspect
import json
import logging
from collections.abc import Callable
from functools import lru_cache

from pydantic_core import PydanticSerializationError, to_jsonable_python

from omniray.tracing import profilers
from omniray.types import IOValue

type JsonSerializable = str | int | float | bool | None | list | dict

logger = logging.getLogger("omniray.tracing")


class IOLogger:
    """Handles I/O logging and serialization of function arguments and results."""

    @classmethod
    def log_input(cls, args: tuple, kwargs: dict, wrapped: Callable, depth: int) -> None:
        """Log function input arguments."""
        formatted_arguments = cls._map_arguments_to_dict(args, kwargs, wrapped)
        if formatted_arguments:
            cls._log_io_block("IN", formatted_arguments, depth)

    @classmethod
    def log_output(cls, result: IOValue, depth: int) -> None:
        """Log function output result."""
        cls._log_io_block("OUT", result, depth)

    @staticmethod
    @lru_cache(maxsize=256)
    def _get_signature(func: Callable) -> inspect.Signature:
        """Cache function signatures to avoid repeated parsing."""
        return inspect.signature(func)

    @classmethod
    def _map_arguments_to_dict(cls, args: tuple, kwargs: dict, wrapped: Callable) -> dict:
        """Map function call arguments to parameter names dictionary for logging."""
        signature = cls._get_signature(wrapped)
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return {
            k: cls._serialize_value(v)
            for k, v in bound.arguments.items()
            if k not in ("self", "cls")
        }

    @staticmethod
    def _serialize_value(value: IOValue) -> JsonSerializable | str:
        """Convert value to JSON-serializable format."""
        try:
            return to_jsonable_python(value)
        except (PydanticSerializationError, TypeError, ValueError):
            return repr(value)

    @staticmethod
    def _format_to_json(value: IOValue) -> str:
        """Format value as pretty JSON string."""
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return repr(value)

    @classmethod
    def _log_io_block(cls, label: str, value: IOValue, depth: int) -> None:
        """Log I/O block with pretty JSON."""
        indent_prefix = profilers.PIPE * depth
        json_str = cls._format_to_json(value)
        lines = json_str.split("\n")
        logger.info("%s%s: %s", indent_prefix, label, lines[0])
        for line in lines[1:]:
            logger.info("%s%s", indent_prefix, line)
