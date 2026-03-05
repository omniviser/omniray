"""Shared fixtures for omniwrap tests."""

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def sys_path_context():
    """Fixture for managing sys.path and sys.modules cleanup."""
    paths_added: list[str] = []
    prefixes: list[str] = []

    def add_path(path: Path, module_prefix: str):
        sys.path.insert(0, str(path))
        paths_added.append(str(path))
        prefixes.append(module_prefix)

    yield add_path

    for path in paths_added:
        sys.path.remove(path)
    for key in list(sys.modules):
        if any(key == p or key.startswith(p + ".") for p in prefixes):
            del sys.modules[key]


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure with Python files."""
    # Create directory structure
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "services").mkdir()
    (tmp_path / "models").mkdir()

    # Create Python files
    (tmp_path / "app" / "main.py").write_text("# main module")
    (tmp_path / "app" / "utils.py").write_text("# utils module")
    (tmp_path / "app" / "services" / "auth.py").write_text("# auth service")
    (tmp_path / "models" / "user.py").write_text("# user model")

    return tmp_path


@pytest.fixture
def tmp_project_with_extras(tmp_project: Path) -> Path:
    """Extend tmp_project with non-Python files and special directories."""
    # Add non-Python files
    (tmp_project / "app" / "config.json").write_text("{}")
    (tmp_project / "README.md").write_text("# README")

    # Add __pycache__
    (tmp_project / "app" / "__pycache__").mkdir()
    (tmp_project / "app" / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"")

    # Add __init__.py files
    (tmp_project / "app" / "__init__.py").write_text("")
    (tmp_project / "models" / "__init__.py").write_text("")

    return tmp_project


@pytest.fixture
def create_pyproject(tmp_path: Path):
    """Factory fixture for creating pyproject.toml with custom omniwrap config."""

    def _create(
        paths: list[str] | None = None,
        exclude: list[str] | None = None,
        skip_wrap: list[str] | None = None,
        *,
        include_tool_section: bool = True,
    ) -> Path:
        lines = ['[project]\nname = "test-project"\n']

        if include_tool_section:
            lines.append("[tool.omniwrap]\n")
            if paths is not None:
                lines.append(f"paths = {paths!r}\n")
            if exclude is not None:
                lines.append(f"exclude = {exclude!r}\n")
            if skip_wrap is not None:
                lines.append(f"skip_wrap = {skip_wrap!r}\n")

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text("".join(lines))
        return pyproject_path

    return _create


@pytest.fixture
def chdir_to_tmp(tmp_path: Path):
    """Change cwd to tmp_path and restore after test."""
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)
