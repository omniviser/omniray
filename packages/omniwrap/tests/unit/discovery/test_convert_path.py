"""Tests for ModuleDiscovery._convert_path_to_module_name.

Correct path-to-module conversion is critical for the import system. Wrong conversion (e.g., missing
dots, wrong prefix) causes ImportError at runtime. These tests ensure paths like 'src/app/main.py'
correctly become 'app.main' and edge cases (files outside root) are handled gracefully.
"""

from pathlib import Path

import pytest
from omniwrap.discovery import ModuleDiscovery


@pytest.mark.parametrize(
    ("py_file", "root_path", "expected"),
    [
        pytest.param(
            Path("src/app/main.py"),
            Path("src"),
            "app.main",
            id="src_root_nested_path",
        ),
        pytest.param(
            Path("src/app/services/auth.py"),
            Path("src"),
            "app.services.auth",
            id="src_root_deeply_nested",
        ),
        pytest.param(
            Path("src/app/__init__.py"),
            Path("src"),
            "app.__init__",
            id="src_root_init_file",
        ),
        pytest.param(
            Path("src/main.py"),
            Path("src"),
            "main",
            id="src_root_file_directly_in_root",
        ),
        pytest.param(
            Path("lib/utils/helpers.py"),
            Path("lib"),
            "utils.helpers",
            id="lib_root_nested_path",
        ),
        pytest.param(
            Path("packages/core/domain/models.py"),
            Path("packages/core"),
            "domain.models",
            id="multi_level_root",
        ),
        pytest.param(
            Path("app/main.py"),
            Path("app"),
            "main",
            id="app_root_single_file",
        ),
        pytest.param(
            Path("myproject/api/v1/endpoints.py"),
            Path("myproject"),
            "api.v1.endpoints",
            id="project_root_with_versioned_path",
        ),
    ],
)
def test_converts_path_to_module_name(py_file, root_path, expected):
    """Test that file paths are correctly converted to Python module names."""
    result = ModuleDiscovery._convert_path_to_module_name(py_file, root_path)

    assert result == expected


def test_returns_none_when_file_outside_root():
    """Test that None is returned when file is not under root_path.

    Prevents crashes when iterating files that somehow end up outside the configured root (e.g.,
    symlinks pointing elsewhere). Without this, Path.relative_to() would raise ValueError.
    """
    py_file = Path("tests/test_main.py")
    root_path = Path("src")

    result = ModuleDiscovery._convert_path_to_module_name(py_file, root_path)

    assert result is None


def test_handles_absolute_paths(tmp_path):
    """Test that absolute paths are handled correctly.

    In production, paths are typically absolute. This ensures the conversion doesn't break when
    given /home/user/project/src/app/main.py instead of relative src/app/main.py.
    """
    root_path = tmp_path / "src"
    py_file = root_path / "app" / "main.py"

    result = ModuleDiscovery._convert_path_to_module_name(py_file, root_path)

    assert result == "app.main"
