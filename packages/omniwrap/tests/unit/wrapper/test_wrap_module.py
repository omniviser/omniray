"""Tests for Wrapper._wrap_module() method."""

from omniwrap.wrapper import Wrapper


def test_skips_when_get_module_attrs_returns_none(mocker, test_module, mock_wrappers_list):
    """Should return early when _get_module_attrs returns None."""
    mocker.patch.object(Wrapper, "_get_module_attrs", return_value=None)
    mock_is_defined = mocker.patch.object(Wrapper, "_is_defined_in_module")
    mock_wrap_object = mocker.patch.object(Wrapper, "_wrap_object")

    Wrapper._wrap_module(test_module, mock_wrappers_list)

    mock_is_defined.assert_not_called()
    mock_wrap_object.assert_not_called()


def test_skips_object_not_defined_in_module(mocker, test_module, mock_wrappers_list):
    """Should skip objects not defined in the module."""

    def external_func():
        pass

    mocker.patch.object(
        Wrapper, "_get_module_attrs", return_value=[("external_func", external_func)]
    )
    mocker.patch.object(Wrapper, "_is_defined_in_module", return_value=False)
    mock_wrap_object = mocker.patch.object(Wrapper, "_wrap_object")

    Wrapper._wrap_module(test_module, mock_wrappers_list)

    mock_wrap_object.assert_not_called()


def test_wraps_object_defined_in_module(mocker, test_module, mock_wrappers_list):
    """Should wrap objects defined in the module."""

    def local_func():
        pass

    mocker.patch.object(Wrapper, "_get_module_attrs", return_value=[("local_func", local_func)])
    mocker.patch.object(Wrapper, "_is_defined_in_module", return_value=True)
    mock_wrap_object = mocker.patch.object(Wrapper, "_wrap_object")

    Wrapper._wrap_module(test_module, mock_wrappers_list)

    mock_wrap_object.assert_called_once_with(
        test_module, "local_func", local_func, mock_wrappers_list, skip_wrap=frozenset()
    )


def test_forwards_skip_wrap_to_wrap_object(mocker, test_module, mock_wrappers_list):
    """Non-empty skip_wrap should be forwarded to _wrap_object."""

    def local_func():
        pass

    mocker.patch.object(Wrapper, "_get_module_attrs", return_value=[("local_func", local_func)])
    mocker.patch.object(Wrapper, "_is_defined_in_module", return_value=True)
    mock_wrap_object = mocker.patch.object(Wrapper, "_wrap_object")

    exclude = frozenset({"to_pydantic"})
    Wrapper._wrap_module(test_module, mock_wrappers_list, skip_wrap=exclude)

    mock_wrap_object.assert_called_once_with(
        test_module,
        "local_func",
        local_func,
        mock_wrappers_list,
        skip_wrap=exclude,
    )


def test_wraps_multiple_objects(mocker, test_module, mock_wrappers_list):
    """Should iterate through and wrap multiple objects."""

    def func1():
        pass

    def func2():
        pass

    mocker.patch.object(
        Wrapper, "_get_module_attrs", return_value=[("func1", func1), ("func2", func2)]
    )
    mocker.patch.object(Wrapper, "_is_defined_in_module", return_value=True)
    mock_wrap_object = mocker.patch.object(Wrapper, "_wrap_object")

    Wrapper._wrap_module(test_module, mock_wrappers_list)

    expected_call_count = 2
    assert mock_wrap_object.call_count == expected_call_count
    mock_wrap_object.assert_any_call(
        test_module, "func1", func1, mock_wrappers_list, skip_wrap=frozenset()
    )
    mock_wrap_object.assert_any_call(
        test_module, "func2", func2, mock_wrappers_list, skip_wrap=frozenset()
    )
