"""Tests for ModuleDiscovery._iter_unique_files.

File iteration must find all .py files recursively while avoiding duplicates. Overlapping paths and
symlinks can cause the same file to be processed twice, leading to duplicate imports and wasted
work. These tests ensure deduplication works correctly.
"""

from omniwrap.discovery import ModuleDiscovery


def test_finds_all_py_files_in_directory(tmp_path, mock_discovery_config):
    """Test that all .py files are found recursively in configured paths.

    Core functionality - if files aren't found, nothing gets imported.
    Tests recursive traversal through nested directories.
    """
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("")
    (tmp_path / "app" / "utils.py").write_text("")
    (tmp_path / "models.py").write_text("")
    config = mock_discovery_config(paths=[tmp_path])

    result = list(ModuleDiscovery._iter_unique_files(config))

    file_names = {py_file.name for py_file, _ in result}
    assert file_names == {"main.py", "utils.py", "models.py"}


def test_deduplicates_overlapping_paths(tmp_path, mock_discovery_config):
    """Test that files are not duplicated when paths overlap.

    Users might configure paths=['src', 'src/app'] by mistake. Without deduplication, files in
    src/app would be imported twice, causing potential issues with module state and wasted
    processing time.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text("")
    (app_dir / "utils.py").write_text("")
    config = mock_discovery_config(paths=[tmp_path, app_dir])
    expected_file_count = 2

    result = list(ModuleDiscovery._iter_unique_files(config))

    resolved_files = [py_file.resolve() for py_file, _ in result]
    assert len(resolved_files) == len(set(resolved_files))
    assert len(resolved_files) == expected_file_count


def test_deduplicates_symlinks(tmp_path, mock_discovery_config):
    """Test that symlinks pointing to the same file are deduplicated.

    Symlinks are common in development setups. Without deduplication via resolve(), the same
    physical file could be imported under different names, causing subtle bugs.
    """
    (tmp_path / "real_module.py").write_text("")
    symlink_path = tmp_path / "link_module.py"
    symlink_path.symlink_to(tmp_path / "real_module.py")
    config = mock_discovery_config(paths=[tmp_path])

    result = list(ModuleDiscovery._iter_unique_files(config))

    assert len(result) == 1


def test_yields_file_with_correct_root_path(tmp_path, mock_discovery_config):
    """Test that each file is yielded with its corresponding root_path.

    The root_path is needed for correct module name conversion. If the wrong root is paired with a
    file, the resulting module name would be incorrect and import would fail.
    """
    root = tmp_path / "src"
    root.mkdir()
    (root / "main.py").write_text("")

    config = mock_discovery_config(paths=[root])

    result = list(ModuleDiscovery._iter_unique_files(config))

    py_file, root_path = result[0]
    assert root_path == root
    assert py_file.is_relative_to(root_path)
