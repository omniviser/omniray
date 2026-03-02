"""Tests for I/O logger module."""

from omniray.tracing import profilers
from omniray.tracing.io_loggers import IOLogger
from pydantic import BaseModel


def test_log_input_with_arguments(mocker):
    """Test log_input logs formatted arguments."""
    mock_log_io_block = mocker.patch.object(IOLogger, "_log_io_block")

    def sample_func(a, b):
        pass

    IOLogger.log_input((1, 2), {}, sample_func, depth=0)

    mock_log_io_block.assert_called_once()
    call_args = mock_log_io_block.call_args[0]
    assert call_args[0] == "IN"
    assert call_args[1] == {"a": 1, "b": 2}


def test_log_input_empty_arguments(mocker):
    """Test log_input does not log when no arguments."""
    mock_log_io_block = mocker.patch.object(IOLogger, "_log_io_block")

    def no_args_func():
        pass

    IOLogger.log_input((), {}, no_args_func, depth=0)

    mock_log_io_block.assert_not_called()


def test_log_output(mocker):
    """Test log_output logs result."""
    mock_log_io_block = mocker.patch.object(IOLogger, "_log_io_block")

    IOLogger.log_output({"result": "value"}, depth=1)

    mock_log_io_block.assert_called_once_with("OUT", {"result": "value"}, 1)


def test_get_signature_caching():
    """Test _get_signature caches function signatures."""

    def test_func(a, b):
        pass

    # First call
    sig1 = IOLogger._get_signature(test_func)
    # Second call - should be cached
    sig2 = IOLogger._get_signature(test_func)

    assert sig1 is sig2


def test_map_arguments_to_dict_with_kwargs():
    """Test _map_arguments_to_dict handles kwargs."""

    def func(a, b=10):
        pass

    result = IOLogger._map_arguments_to_dict((1,), {"b": 20}, func)

    assert result == {"a": 1, "b": 20}


def test_serialize_value_jsonable():
    """Test _serialize_value returns jsonable python for pydantic models."""

    class MyModel(BaseModel):
        name: str
        value: int

    model = MyModel(name="test", value=42)
    result = IOLogger._serialize_value(model)

    assert result == {"name": "test", "value": 42}


def test_serialize_value_primitive():
    """Test _serialize_value handles primitive types."""
    int_value = 42
    assert IOLogger._serialize_value(int_value) == int_value
    assert IOLogger._serialize_value("hello") == "hello"
    assert IOLogger._serialize_value([1, 2, 3]) == [1, 2, 3]


def test_serialize_value_fallback_repr():
    """Test _serialize_value falls back to repr on error."""

    class Unserializable:
        def __repr__(self):
            return "<Unserializable>"

    obj = Unserializable()
    result = IOLogger._serialize_value(obj)

    assert result == "<Unserializable>"


def test_format_to_json_success():
    """Test _format_to_json formats dict as pretty JSON."""
    result = IOLogger._format_to_json({"key": "value"})

    assert '"key": "value"' in result


def test_format_to_json_fallback_repr():
    """Test _format_to_json falls back to repr on error."""

    class NotJsonable:
        pass

    obj = NotJsonable()
    result = IOLogger._format_to_json(obj)

    assert "NotJsonable" in result


def test_log_io_block_single_line(mocker):
    """Test _log_io_block logs single line JSON."""
    mock_logger = mocker.patch("omniray.tracing.io_loggers.logger")

    IOLogger._log_io_block("IN", "simple", depth=0)

    mock_logger.info.assert_called()


def test_log_io_block_multiline(mocker):
    """Test _log_io_block logs multiline JSON correctly."""
    mock_logger = mocker.patch("omniray.tracing.io_loggers.logger")

    IOLogger._log_io_block("OUT", {"a": 1, "b": 2}, depth=1)

    # Should log multiple lines (header + continuation)
    assert mock_logger.info.call_count >= 1


def test_log_io_block_uses_profilers_pipe(mocker, monkeypatch):
    """Test _log_io_block uses profilers.PIPE for indent prefix."""
    mock_logger = mocker.patch("omniray.tracing.io_loggers.logger")
    monkeypatch.setattr(profilers, "PIPE", "|  ")

    IOLogger._log_io_block("IN", "value", depth=2)

    first_call_args = mock_logger.info.call_args_list[0][0]
    assert first_call_args[1].startswith("|  |  ")
