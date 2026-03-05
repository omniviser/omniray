"""Console logger setup for tree output."""

import logging

logger = logging.getLogger("omniray.tracing")


def setup_console_handler() -> None:
    """Add console handler if not already present.

    Omniray owns its handler (like pytest/tqdm) — colored tree output would be
    garbled by app-level formatters.  ``propagate=False`` prevents double output.
    To silence at runtime: ``logging.getLogger("omniray.tracing").setLevel(CRITICAL)``
    """
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s  %(levelname)s: %(message)s", datefmt="%H:%M")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
