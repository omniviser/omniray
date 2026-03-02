"""E2E tests for import filtering — imported functions must NOT be wrapped."""

from omniwrap.wrapper import Wrapper

MODULE_WITH_STDLIB_IMPORTS = """
from os.path import join
import json

def my_func(x):
    return json.dumps({"x": x})
"""

MODULE_WITH_THIRD_PARTY_IMPORT = """
import wrapt

def process(x):
    return f"processed {x}"
"""

MODULE_WITH_CROSS_MODULE_IMPORT = """
from os.path import basename

def transform(path):
    return basename(path).upper()
"""


def test_stdlib_imports_not_wrapped(create_module, calls, sync_wrapper_factory):
    """Imported stdlib functions (os.path.join, json) must NOT be wrapped."""
    config = create_module(MODULE_WITH_STDLIB_IMPORTS)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import join, my_func  # noqa: PLC0415

    my_func("test")
    assert calls == ["w_before", "w_after"]

    calls.clear()
    result = join("/tmp", "file")
    assert result == "/tmp/file"
    assert calls == []


def test_third_party_imports_not_wrapped(create_module, calls, sync_wrapper_factory):
    """Imported third-party functions must NOT be wrapped."""
    config = create_module(MODULE_WITH_THIRD_PARTY_IMPORT)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import process  # noqa: PLC0415

    process("x")
    assert calls == ["w_before", "w_after"]


def test_cross_module_import_not_wrapped(create_module, calls, sync_wrapper_factory):
    """Imported function from another stdlib module must NOT be wrapped."""
    config = create_module(MODULE_WITH_CROSS_MODULE_IMPORT)

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import basename, transform  # noqa: PLC0415

    transform("/tmp/file.txt")
    assert calls == ["w_before", "w_after"]

    calls.clear()
    basename("/tmp/file.txt")
    assert calls == []


def test_module_with_many_imports_only_wraps_local(create_modules, calls, sync_wrapper_factory):
    """Multiple modules with cross-imports — only locally defined functions wrapped."""
    config = create_modules(
        {
            "myapp/service.py": (
                "from myapp.utils import helper\n"
                "\n"
                "def process(x):\n"
                '    return helper(x) + " processed"\n'
            ),
            "myapp/utils.py": ('def helper(x):\n    return f"helped {x}"\n'),
        }
    )

    Wrapper.wrap_all(sync_wrapper_factory("w"), config=config)

    from myapp.service import helper as imported_helper  # noqa: PLC0415
    from myapp.service import process  # noqa: PLC0415
    from myapp.utils import helper  # noqa: PLC0415

    # process is defined in myapp.service — should be wrapped
    process("x")
    assert calls == ["w_before", "w_after"]

    # helper accessed via myapp.utils — wrapped (wrapt replaced the attribute)
    calls.clear()
    helper("y")
    assert calls == ["w_before", "w_after"]

    # helper imported INTO myapp.service points to the original function object
    # (not the FunctionWrapper), because wrapt replaces the module attribute,
    # not the function object itself. So the import-time binding is stale.
    calls.clear()
    imported_helper("z")
    assert calls == []
