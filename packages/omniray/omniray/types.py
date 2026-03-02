"""Type aliases for omniray."""

from typing import Any

type WraptInstance = Any  # None (function/static), class (classmethod), or object (method)
type CallResult = Any  # Return value from wrapped function call
type IOValue = Any  # Function argument or return value for logging
