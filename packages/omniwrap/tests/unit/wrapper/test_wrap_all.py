"""Tests for Wrapper.wrap_all() method."""

from types import ModuleType

from omniwrap.config import DiscoveryConfig
from omniwrap.discovery import ModuleDiscovery
from omniwrap.wrapper import Wrapper


def test_single_wrapper_normalized_to_pair(mocker):
    """Single wrapper should be normalized to (wrapper, wrapper) pair."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mocker.patch.object(ModuleDiscovery, "discover", return_value=[])
    mock_normalize = mocker.patch.object(Wrapper, "_normalize_wrappers", return_value=[])
    single_wrapper = mocker.MagicMock(name="single")

    Wrapper.wrap_all(single_wrapper)

    mock_normalize.assert_called_once_with((single_wrapper,))


def test_tuple_wrappers_passed_as_variadic(mocker):
    """Tuple of (sync, async) wrappers should be passed through variadic args."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mocker.patch.object(ModuleDiscovery, "discover", return_value=[])
    mock_normalize = mocker.patch.object(Wrapper, "_normalize_wrappers", return_value=[])

    sync_wrapper = mocker.MagicMock(name="sync")
    async_wrapper = mocker.MagicMock(name="async")

    Wrapper.wrap_all((sync_wrapper, async_wrapper))

    mock_normalize.assert_called_once_with(((sync_wrapper, async_wrapper),))


def test_enabled_true_wraps(mocker):
    """Enabled=True should proceed with wrapping."""
    mock_discover = mocker.patch.object(ModuleDiscovery, "discover", return_value=[])

    Wrapper.wrap_all(mocker.MagicMock(), enabled=True)

    mock_discover.assert_called_once()


def test_enabled_false_skips(mocker):
    """Enabled=False should skip wrapping entirely."""
    mock_discover = mocker.patch.object(ModuleDiscovery, "discover", return_value=[])

    Wrapper.wrap_all(mocker.MagicMock(), enabled=False)

    mock_discover.assert_not_called()


def test_config_none_loads_from_pyproject(mocker):
    """Config=None should load from pyproject and pass resolved config to discover."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mock_from_pyproject = mocker.patch.object(DiscoveryConfig, "from_pyproject")
    mock_discover = mocker.patch.object(ModuleDiscovery, "discover", return_value=[])

    Wrapper.wrap_all(mocker.MagicMock(), config=None)

    mock_from_pyproject.assert_called_once()
    mock_discover.assert_called_once_with(mock_from_pyproject.return_value)


def test_custom_config_passed_to_discover(mocker):
    """Custom config should be passed to discover."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mock_discover = mocker.patch.object(ModuleDiscovery, "discover", return_value=[])

    custom_config = mocker.MagicMock(name="custom_config")

    Wrapper.wrap_all(mocker.MagicMock(), config=custom_config)

    mock_discover.assert_called_once_with(custom_config)


def test_wraps_discovered_modules(mocker):
    """Each discovered module should be wrapped with the normalized wrappers list."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)

    module1 = ModuleType("module1")
    module2 = ModuleType("module2")
    mocker.patch.object(ModuleDiscovery, "discover", return_value=[module1, module2])

    mock_wrap_module = mocker.patch.object(Wrapper, "_wrap_module")
    wrapper = mocker.MagicMock(name="wrapper")

    config = DiscoveryConfig()
    Wrapper.wrap_all(wrapper, config=config)

    expected_normalized = [(wrapper, wrapper)]
    expected_call_count = 2
    assert mock_wrap_module.call_count == expected_call_count
    mock_wrap_module.assert_any_call(module1, expected_normalized, skip_wrap=config.skip_wrap)
    mock_wrap_module.assert_any_call(module2, expected_normalized, skip_wrap=config.skip_wrap)


def test_empty_modules_list_no_crash(mocker):
    """Empty modules list should not cause any issues."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mocker.patch.object(ModuleDiscovery, "discover", return_value=[])
    mock_wrap_module = mocker.patch.object(Wrapper, "_wrap_module")

    Wrapper.wrap_all(mocker.MagicMock())

    mock_wrap_module.assert_not_called()


def test_multiple_wrappers_normalized_and_passed(mocker):
    """Multiple variadic wrappers should all be passed to _wrap_module."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    module1 = ModuleType("module1")
    mocker.patch.object(ModuleDiscovery, "discover", return_value=[module1])
    mock_wrap_module = mocker.patch.object(Wrapper, "_wrap_module")

    w1 = mocker.MagicMock(name="w1")
    w2 = mocker.MagicMock(name="w2")

    config = DiscoveryConfig()
    Wrapper.wrap_all(w1, w2, config=config)

    expected_normalized = [(w1, w1), (w2, w2)]
    mock_wrap_module.assert_called_once_with(
        module1, expected_normalized, skip_wrap=config.skip_wrap
    )


def test_discovery_happens_once_with_multiple_wrappers(mocker):
    """Discovery should happen exactly once regardless of wrapper count."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mock_discover = mocker.patch.object(ModuleDiscovery, "discover", return_value=[])
    mocker.patch.object(Wrapper, "_wrap_module")

    Wrapper.wrap_all(mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock())

    mock_discover.assert_called_once()


def test_no_wrappers_no_crash(mocker):
    """Calling wrap_all() with no wrappers should not crash."""
    mocker.patch.object(Wrapper, "_should_wrap", return_value=True)
    mocker.patch.object(ModuleDiscovery, "discover", return_value=[ModuleType("m")])
    mock_wrap_module = mocker.patch.object(Wrapper, "_wrap_module")

    Wrapper.wrap_all()

    mock_wrap_module.assert_called_once_with(mocker.ANY, [], skip_wrap=frozenset())
