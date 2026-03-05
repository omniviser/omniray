"""Unit tests for console handler setup."""

import logging

from omniray.tracing.console import setup_console_handler


def test_setup_console_handler_adds_handler(mocker):
    """Test setup_console_handler adds handler when logger has none."""
    mocker.patch("omniray.tracing.console.logger.handlers", new=[])
    setup_console_handler()
    from omniray.tracing.console import logger as console_logger  # noqa: PLC0415

    assert len(console_logger.handlers) > 0
    assert console_logger.level == logging.INFO
    assert console_logger.propagate is False
    # Cleanup
    console_logger.handlers.clear()


def test_setup_console_handler_idempotent(mocker):
    """Test setup_console_handler does not add duplicate handlers."""
    mock_handler = mocker.MagicMock()
    mocker.patch("omniray.tracing.console.logger.handlers", new=[mock_handler])
    setup_console_handler()
    from omniray.tracing.console import logger as console_logger  # noqa: PLC0415

    assert len(console_logger.handlers) == 1


def test_eager_console_init_on_import(mocker):
    """Test that importing tracers calls setup_console_handler when CONSOLE_LOG_FLAG is True."""
    import importlib  # noqa: PLC0415

    mocker.patch("omniray.tracing.flags.CONSOLE_LOG_FLAG", new=True)
    mock_setup = mocker.patch("omniray.tracing.console.setup_console_handler")
    import omniray.tracing.tracers  # noqa: PLC0415

    importlib.reload(omniray.tracing.tracers)
    mock_setup.assert_called_once()
