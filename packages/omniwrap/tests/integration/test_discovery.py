"""Integration tests for ModuleDiscovery.discover and _discover_module_names.

These tests verify the full discovery pipeline with real files and imports.
Unit tests cover individual methods in isolation, but integration tests catch
issues in how components work together - e.g., config filtering combined with
actual file system traversal and Python import machinery.
"""

from pathlib import Path
from types import ModuleType

import pytest
from omniwrap.config import DiscoveryConfig
from omniwrap.discovery import ModuleDiscovery

pytestmark = pytest.mark.integration


def create_package(base_path: Path, name: str, modules: list[str] | None = None) -> Path:
    """Create a Python package with __init__.py and optional modules."""
    pkg = base_path / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(f'"""{name} package."""')
    for mod in modules or []:
        (pkg / mod).write_text(f'"""{mod.removesuffix(".py")} module."""')
    return pkg


@pytest.fixture
def importable_project(tmp_path, sys_path_context):
    """Create a temporary Python package that can be imported.

    Structure: testpkg/{module_a.py, module_b.py, subpkg/module_c.py}
    """
    create_package(tmp_path, "testpkg", ["module_a.py", "module_b.py"])
    create_package(tmp_path / "testpkg", "subpkg", ["module_c.py"])
    sys_path_context(tmp_path, "testpkg")
    return tmp_path


@pytest.fixture
def multi_path_project(tmp_path, sys_path_context):
    """Create a project with multiple source directories.

    Structure: src/pkg_one/service.py, lib/pkg_two/utils.py
    """
    src_dir = tmp_path / "src"
    lib_dir = tmp_path / "lib"
    create_package(src_dir, "pkg_one", ["service.py"])
    create_package(lib_dir, "pkg_two", ["utils.py"])
    sys_path_context(src_dir, "pkg_one")
    sys_path_context(lib_dir, "pkg_two")
    return {"src": src_dir, "lib": lib_dir}


@pytest.fixture
def overlapping_paths_project(tmp_path, sys_path_context):
    """Create a project where one path is nested inside another.

    Structure: src/mypkg/{core.py, subpkg/helper.py}
    """
    src_dir = tmp_path / "src"
    create_package(src_dir, "mypkg", ["core.py"])
    create_package(src_dir / "mypkg", "subpkg", ["helper.py"])
    sys_path_context(src_dir, "mypkg")
    return {"src": src_dir, "subpkg": src_dir / "mypkg" / "subpkg"}


@pytest.fixture
def deeply_nested_project(tmp_path, sys_path_context):
    """Create a project with deeply nested package structure.

    Structure: src/api/v1/endpoints/users/handlers.py
    """
    src_dir = tmp_path / "src"
    create_package(src_dir, "api")
    create_package(src_dir / "api", "v1")
    create_package(src_dir / "api" / "v1", "endpoints")
    create_package(src_dir / "api" / "v1" / "endpoints", "users", ["handlers.py"])
    sys_path_context(src_dir, "api")
    return src_dir


@pytest.fixture
def symlinked_project(tmp_path, sys_path_context):
    """Create a project with symlinked package.

    Structure: src/realpkg/module.py, linked/linkedpkg -> src/realpkg
    """
    src_dir = tmp_path / "src"
    link_dir = tmp_path / "linked"
    link_dir.mkdir()

    create_package(src_dir, "realpkg", ["module.py"])
    (link_dir / "linkedpkg").symlink_to(src_dir / "realpkg")

    sys_path_context(src_dir, "realpkg")
    sys_path_context(link_dir, "linkedpkg")
    return {"src": src_dir, "linked": link_dir}


@pytest.fixture
def project_with_omniwrap_dir(tmp_path, sys_path_context):
    """Create a project containing an omniwrap-like directory.

    Structure: src/{omniwrap/wrapper.py, myapp/main.py}
    Used to test that omniwrap self-exclusion works correctly.
    """
    src_dir = tmp_path / "src"
    create_package(src_dir, "omniwrap", ["wrapper.py"])
    create_package(src_dir, "myapp", ["main.py"])
    sys_path_context(src_dir, "omniwrap")
    sys_path_context(src_dir, "myapp")
    return src_dir


@pytest.fixture
def project_with_test_files(importable_project):
    """Add test files to importable_project for glob pattern testing."""
    testpkg = importable_project / "testpkg"
    (testpkg / "test_something.py").write_text('"""Test file."""')
    (testpkg / "something_test.py").write_text('"""Another test file."""')
    (testpkg / "conftest.py").write_text('"""Conftest."""')
    return importable_project


@pytest.fixture
def project_with_default_excludes(tmp_path, sys_path_context):
    """Create a project with directories that should be excluded by default.

    Structure: src/myapp/main.py + .venv/ and __pycache__/ with modules
    """
    src_dir = tmp_path / "src"
    create_package(src_dir, "myapp", ["main.py"])

    # Create modules in directories that should be excluded by default
    venv_pkg = src_dir / ".venv" / "lib" / "somepkg"
    venv_pkg.mkdir(parents=True)
    (venv_pkg / "__init__.py").write_text('"""Venv package."""')
    (venv_pkg / "module.py").write_text('"""Venv module."""')

    pycache_dir = src_dir / "myapp" / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "cached.py").write_text('"""Cached."""')

    sys_path_context(src_dir, "myapp")
    return src_dir


@pytest.fixture
def project_with_init_and_main(tmp_path, sys_path_context):
    """Create a project with __init__.py, __main__.py and regular module.

    Structure: src/myapp/{__init__.py, __main__.py, core.py}
    """
    src_dir = tmp_path / "src"
    pkg = src_dir / "myapp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""Init."""')
    (pkg / "__main__.py").write_text('"""Main entry."""')
    (pkg / "core.py").write_text('"""Core module."""')

    sys_path_context(src_dir, "myapp")
    return src_dir


@pytest.fixture
def project_with_broken_module(importable_project):
    """Add a module with broken import to importable_project.

    Adds testpkg/broken.py that tries to import a nonexistent dependency, causing ImportError when
    imported. Used to test graceful handling of import failures.
    """
    broken_file = importable_project / "testpkg" / "broken.py"
    broken_file.write_text("import nonexistent_dependency_xyz_123")
    return importable_project


@pytest.fixture
def discovery_config_for_testpkg(importable_project):
    """Create a DiscoveryConfig for the test package.

    This config will discover all .py files in testpkg/.
    """
    return DiscoveryConfig(
        paths=(importable_project,),
        exclude=frozenset(),
    )


@pytest.mark.usefixtures("importable_project")
def test_discovers_all_modules_in_paths(discovery_config_for_testpkg):
    """Test that all Python modules in configured paths are discovered and imported.

    Core test - verifies the entire pipeline from config to
    imported modules works correctly with a real package structure.
    """
    result = ModuleDiscovery.discover(discovery_config_for_testpkg)

    module_names = {mod.__name__ for mod in result}
    assert "testpkg.module_a" in module_names
    assert "testpkg.module_b" in module_names
    assert "testpkg.subpkg.module_c" in module_names


@pytest.mark.usefixtures("importable_project")
def test_returns_module_type_objects(discovery_config_for_testpkg):
    """Test that discover() returns actual ModuleType objects.

    Ensures callers receive real module objects they can introspect and wrap, not just module names
    or paths.
    """
    result = ModuleDiscovery.discover(discovery_config_for_testpkg)

    assert all(isinstance(mod, ModuleType) for mod in result)


@pytest.mark.usefixtures("project_with_broken_module")
def test_skips_modules_with_import_error(discovery_config_for_testpkg):
    """Test that modules with import errors are skipped without crashing.

    Real projects may have modules with missing optional dependencies. Discovery must continue
    processing other modules instead of failing completely on the first broken import.
    """
    result = ModuleDiscovery.discover(discovery_config_for_testpkg)

    module_names = {mod.__name__ for mod in result}
    assert "testpkg.broken" not in module_names
    assert "testpkg.module_a" in module_names


def test_filters_modules_with_should_import(importable_project):
    """Test that exclude_patterns in config filters out matching modules.

    Users need to exclude test files, migrations, etc. This verifies the filtering actually prevents
    those modules from being imported.
    """
    config = DiscoveryConfig(
        paths=(importable_project,),
        exclude=frozenset({"module_b.py"}),
    )

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "testpkg.module_a" in module_names
    assert "testpkg.module_b" not in module_names


def test_handles_empty_paths():
    """Test that empty paths configuration returns empty list.

    Graceful handling of edge case - empty config shouldn't crash
    or return unexpected results.
    """
    config = DiscoveryConfig(
        paths=(),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    assert result == []


def test_uses_default_config_when_none(mocker):
    """Test that discover(config=None) loads config from pyproject.toml.

    Convenience feature - users can call discover() without explicitly
    creating a config, and it will use project defaults.
    """
    mock_from_pyproject = mocker.patch.object(
        DiscoveryConfig,
        "from_pyproject",
        return_value=DiscoveryConfig(
            paths=(),
            exclude=frozenset(),
        ),
    )

    ModuleDiscovery.discover(config=None)

    mock_from_pyproject.assert_called_once()


@pytest.mark.usefixtures("importable_project")
def test_discover_module_names_yields_valid_names(discovery_config_for_testpkg):
    """Test that _discover_module_names yields correct module name strings.

    Verifies the intermediate step - module names must be valid Python
    import paths before we attempt to import them.
    """
    result = list(ModuleDiscovery._discover_module_names(discovery_config_for_testpkg))

    assert "testpkg.module_a" in result
    assert "testpkg.module_b" in result
    assert "testpkg.subpkg.module_c" in result


def test_discover_module_names_respects_should_import_filter(importable_project, mocker):
    """Test that _discover_module_names respects config.should_import filter.

    Filtering happens before import attempt - this saves time by not
    trying to import modules we know we don't want.
    """
    config = mocker.Mock()
    config.paths = [importable_project]
    config.should_import = lambda path: "module_a" in str(path)

    result = list(ModuleDiscovery._discover_module_names(config))

    assert "testpkg.module_a" in result
    assert "testpkg.module_b" not in result


def test_discover_module_names_skips_files_outside_root_path(importable_project):
    """Test that files outside configured paths are not discovered.

    Security/correctness check - only files under configured paths
    should be discovered, not random files elsewhere in the filesystem.
    """
    other_dir = importable_project / "other"
    other_dir.mkdir()
    (other_dir / "outside.py").write_text("")

    config = DiscoveryConfig(
        paths=(importable_project / "testpkg",),
        exclude=frozenset(),
    )

    result = list(ModuleDiscovery._discover_module_names(config))

    assert not any("outside" in name for name in result)


def test_discovers_modules_from_multiple_paths(multi_path_project):
    """Test that modules from multiple configured paths are all discovered.

    Real projects often have multiple source directories (e.g., src/ and lib/). Discovery must
    traverse all configured paths and import modules from each.
    """
    config = DiscoveryConfig(
        paths=(multi_path_project["src"], multi_path_project["lib"]),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "pkg_one.service" in module_names
    assert "pkg_two.utils" in module_names


def test_deduplicates_modules_when_paths_overlap(overlapping_paths_project):
    """Test that overlapping paths don't cause duplicate module imports.

    If paths=(src/, src/subpkg/), module src/subpkg/mod.py could be found twice. Discovery must
    deduplicate to avoid importing the same module multiple times.
    """
    config = DiscoveryConfig(
        paths=(overlapping_paths_project["src"], overlapping_paths_project["subpkg"]),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    module_names = [mod.__name__ for mod in result]
    assert module_names.count("mypkg.subpkg.helper") == 1


def test_excludes_directories_from_discovery(importable_project):
    """Test that directories in exclude config are skipped entirely.

    Different from exclude_patterns (which matches file names).
    Exclude skips entire directory trees - useful for ignoring
    migrations/, tests/, or vendor/ directories.
    """
    config = DiscoveryConfig(
        paths=(importable_project,),
        exclude=frozenset({"subpkg"}),
    )

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "testpkg.module_a" in module_names
    assert "testpkg.module_b" in module_names
    assert "testpkg.subpkg.module_c" not in module_names


def test_discovers_deeply_nested_modules(deeply_nested_project):
    """Test that deeply nested package structures are discovered correctly.

    Some projects have deep hierarchies like api/v1/endpoints/users.py. Discovery must handle
    arbitrary nesting depth.
    """
    config = DiscoveryConfig(
        paths=(deeply_nested_project,),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "api.v1.endpoints.users.handlers" in module_names


def test_handles_nonexistent_path_gracefully(tmp_path):
    """Test that non-existent paths in config don't crash discovery.

    User misconfiguration (typo in path, deleted directory) should not
    cause the entire discovery to fail - just skip that path.
    """
    nonexistent = tmp_path / "does_not_exist"
    config = DiscoveryConfig(
        paths=(nonexistent,),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    assert result == []


def test_handles_symlinked_files(symlinked_project):
    """Test that symlinked files are discovered and deduplicated correctly.

    Symlinks can cause the same file to appear multiple times under different paths. Discovery must
    resolve symlinks to avoid duplicates.
    """
    config = DiscoveryConfig(
        paths=(symlinked_project["src"], symlinked_project["linked"]),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    module_names = [mod.__name__ for mod in result]
    module_count = sum(1 for name in module_names if "module" in name)
    assert module_count == 1


def test_exclude_patterns_support_glob_wildcards(project_with_test_files):
    """Test that exclude_patterns supports glob-style wildcards.

    Users need patterns like 'test_*.py' or '*_test.py' to exclude test files. fnmatch patterns must
    work correctly.
    """
    config = DiscoveryConfig(
        paths=(project_with_test_files,),
        exclude=frozenset({"test_*.py", "*_test.py", "conftest.py"}),
    )

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "testpkg.module_a" in module_names
    assert "testpkg.test_something" not in module_names
    assert "testpkg.something_test" not in module_names
    assert "testpkg.conftest" not in module_names


def test_excludes_omniwrap_package_from_discovery(project_with_omniwrap_dir):
    """Test that omniwrap package is always excluded from discovery.

    Critical safety feature - omniwrap must never instrument itself,
    which would cause infinite recursion. The '/omniwrap/' check in
    path ensures this package is always skipped.
    """
    config = DiscoveryConfig(
        paths=(project_with_omniwrap_dir,),
        exclude=frozenset(),
    )

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "myapp.main" in module_names
    assert "omniwrap.wrapper" not in module_names


def test_excludes_default_directories(project_with_default_excludes):
    """Test that default excluded directories are skipped.

    Directories like .venv, __pycache__, .git should be excluded by default without explicit
    configuration. This prevents accidental instrumentation of virtual environments and cache files.
    """
    config = DiscoveryConfig(paths=(project_with_default_excludes,))

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "myapp.main" in module_names
    assert not any(".venv" in name for name in module_names)
    assert not any("__pycache__" in name for name in module_names)


def test_skips_init_and_main_files_by_default(project_with_init_and_main):
    """Test that __init__.py and __main__.py are excluded by default.

    These files are typically not useful for instrumentation:
    - __init__.py often just re-exports or is empty
    - __main__.py is entry point, not library code
    """
    config = DiscoveryConfig(paths=(project_with_init_and_main,))

    result = ModuleDiscovery.discover(config)

    module_names = {mod.__name__ for mod in result}
    assert "myapp.core" in module_names
    assert "myapp.__init__" not in module_names
    assert "myapp.__main__" not in module_names
