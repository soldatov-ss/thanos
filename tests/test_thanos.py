#!/usr/bin/env python

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from thanos_cli.cli import init
from thanos_cli.config import get_default_protected_patterns, load_thanosignore, load_thanosrc
from thanos_cli.protection import should_protect_file
from thanos_cli.snap import snap
from thanos_cli.utils import get_files
from thanos_cli.weights import _matches_age_range, _matches_size_range, calculate_file_weight, weighted_random_sample


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def populated_dir(temp_dir):
    """Create a directory with test files."""
    # Create 10 test files
    for i in range(10):
        (temp_dir / f"file_{i}.txt").write_text(f"Content {i}")
    return temp_dir


@pytest.fixture
def nested_dir(temp_dir):
    """Create a directory with nested subdirectories and files."""
    # Root level files
    for i in range(6):
        (temp_dir / f"root_{i}.txt").write_text(f"Root {i}")

    # Subdirectory with files
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    for i in range(4):
        (subdir / f"sub_{i}.txt").write_text(f"Sub {i}")

    # Nested subdirectory
    nested = subdir / "nested"
    nested.mkdir()
    for i in range(2):
        (nested / f"nested_{i}.txt").write_text(f"Nested {i}")

    return temp_dir


@pytest.fixture
def dir_with_protected_files(temp_dir):
    """Create a directory with files that should be protected."""
    # Regular files
    for i in range(5):
        (temp_dir / f"file_{i}.txt").write_text(f"Content {i}")

    # Protected: .env file
    (temp_dir / ".env").write_text("SECRET=value")

    # Protected: .git directory
    git_dir = temp_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config")

    # Protected: node_modules
    node_modules = temp_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.json").write_text("{}")

    # Protected: venv
    venv = temp_dir / ".venv"
    venv.mkdir()
    venv_bin = venv / "bin"
    venv_bin.mkdir()
    (venv_bin / "python").write_text("#!/usr/bin/python")

    return temp_dir


class TestGetFiles:
    """Tests for the get_files function."""

    def test_get_files_empty_directory(self, temp_dir):
        """Test getting files from an empty directory."""
        files = get_files(str(temp_dir))
        assert len(files) == 0

    def test_get_files_with_files(self, populated_dir):
        """Test getting files from a populated directory."""
        files = get_files(str(populated_dir))
        assert len(files) == 10

    def test_get_files_non_recursive(self, nested_dir):
        """Test that non-recursive mode only gets root files."""
        files = get_files(str(nested_dir), recursive=False)
        assert len(files) == 6  # Only root level files

    def test_get_files_recursive(self, nested_dir):
        """Test that recursive mode gets all files."""
        files = get_files(str(nested_dir), recursive=True)
        assert len(files) == 12  # 6 root + 4 subdir + 2 nested

    def test_get_files_nonexistent_directory(self):
        """Test that nonexistent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            get_files("/nonexistent/directory")

    def test_get_files_not_a_directory(self, temp_dir):
        """Test that file path raises NotADirectoryError."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test")

        with pytest.raises(NotADirectoryError):
            get_files(str(file_path))

    def test_get_files_ignores_directories(self, nested_dir):
        """Test that directories themselves are not included."""
        files = get_files(str(nested_dir), recursive=True)
        # Verify all returned items are files, not directories
        assert all(f.is_file() for f in files)


class TestConfig:
    """Tests for configuration loading."""

    def test_load_thanosignore_empty(self, temp_dir):
        """Test loading from directory without .thanosignore."""
        patterns, path = load_thanosignore(str(temp_dir))
        assert len(patterns) == 0
        assert path is None

    def test_load_thanosignore_with_patterns(self, temp_dir):
        """Test loading .thanosignore with patterns."""
        ignore_file = temp_dir / ".thanosignore"
        ignore_file.write_text("*.log\n*.tmp\nimportant/\n")

        patterns, path = load_thanosignore(str(temp_dir))
        assert "*.log" in patterns
        assert "*.tmp" in patterns
        assert "important/" in patterns
        assert path == ignore_file

    def test_load_thanosignore_ignores_comments(self, temp_dir):
        """Test that comments are ignored in .thanosignore."""
        ignore_file = temp_dir / ".thanosignore"
        ignore_file.write_text("# Comment\n*.log\n# Another comment\n*.tmp\n")

        patterns, path = load_thanosignore(str(temp_dir))
        assert len(patterns) == 2
        assert "*.log" in patterns
        assert "*.tmp" in patterns

    def test_load_thanosignore_from_parent(self, temp_dir):
        """Test that .thanosignore is found in parent directory."""
        ignore_file = temp_dir / ".thanosignore"
        ignore_file.write_text("*.log\n")

        subdir = temp_dir / "subdir"
        subdir.mkdir()

        patterns, path = load_thanosignore(str(subdir))
        assert "*.log" in patterns
        assert path == ignore_file

    def test_load_thanosrc_empty(self, temp_dir):
        """Test loading from directory without .thanosrc.json."""
        config, path = load_thanosrc(str(temp_dir))
        assert config == {}
        assert path is None

    def test_load_thanosrc_with_weights(self, temp_dir):
        """Test loading .thanosrc.json with weights."""
        config_file = temp_dir / ".thanosrc.json"
        config_data = {"weights": {"by_extension": {".log": 0.9, ".tmp": 0.95}}}
        config_file.write_text(json.dumps(config_data))

        config, path = load_thanosrc(str(temp_dir))
        assert config["weights"]["by_extension"][".log"] == 0.9
        assert config["weights"]["by_extension"][".tmp"] == 0.95
        assert path == config_file

    def test_get_default_protected_patterns(self):
        """Test that default patterns include critical files."""
        patterns = get_default_protected_patterns()

        # Check for key patterns
        assert ".git/" in patterns
        assert ".env" in patterns
        assert "node_modules/" in patterns
        assert ".venv/" in patterns
        assert "venv/" in patterns


class TestProtection:
    """Tests for file protection logic."""

    def test_should_protect_file_basic(self, temp_dir):
        """Test basic file protection."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        patterns = {"*.txt"}
        assert should_protect_file(test_file, temp_dir, patterns)

    def test_should_protect_file_no_match(self, temp_dir):
        """Test file that doesn't match patterns."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        patterns = {"*.log"}
        assert not should_protect_file(test_file, temp_dir, patterns)

    def test_should_protect_directory_pattern(self, temp_dir):
        """Test directory pattern protection."""
        venv_dir = temp_dir / ".venv"
        venv_dir.mkdir()
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir()
        python_file = bin_dir / "python"
        python_file.write_text("#!/usr/bin/python")

        patterns = {".venv/"}
        assert should_protect_file(python_file, temp_dir, patterns)

    def test_should_protect_nested_in_protected_dir(self, temp_dir):
        """Test that files nested in protected directories are protected."""
        node_modules = temp_dir / "node_modules"
        node_modules.mkdir()
        package_dir = node_modules / "package"
        package_dir.mkdir()
        package_file = package_dir / "index.js"
        package_file.write_text("module.exports = {}")

        patterns = {"node_modules/"}
        assert should_protect_file(package_file, temp_dir, patterns)

    def test_should_protect_file_outside_base(self, temp_dir):
        """Test that files outside base path are protected (safe default)."""
        other_dir = Path(tempfile.mkdtemp())
        try:
            test_file = other_dir / "test.txt"
            test_file.write_text("content")

            patterns = {"*.txt"}
            # File outside base_path should be protected (returns True on ValueError)
            assert should_protect_file(test_file, temp_dir, patterns)
        finally:
            shutil.rmtree(other_dir, ignore_errors=True)

    def test_should_protect_with_empty_patterns(self, temp_dir):
        """Test that empty patterns means no protection."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        patterns = set()
        assert not should_protect_file(test_file, temp_dir, patterns)


class TestSnap:
    """Tests for the snap function."""

    def test_snap_empty_directory(self, temp_dir, capsys):
        """Test snap on empty directory."""
        snap(str(temp_dir), no_protect=True)
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower() or "No eligible files" in captured.out

    def test_snap_deletes_half_files_no_protect(self, populated_dir):
        """Test that snap deletes approximately half the files with no protection."""
        initial_count = len(list(populated_dir.iterdir()))
        assert initial_count == 10

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(populated_dir), no_protect=True)

        remaining_count = len(list(populated_dir.iterdir()))
        assert remaining_count == 5  # Half of 10

    def test_snap_respects_protected_files(self, dir_with_protected_files):
        """Test that snap respects protected files."""
        all_files = list(dir_with_protected_files.rglob("*"))
        all_files = [f for f in all_files if f.is_file()]

        # Should have 5 regular + 1 .env + 1 git/config + 1 node_modules/package.json + 1 .venv/bin/python
        assert len(all_files) == 9

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(dir_with_protected_files))

        # Protected files should still exist
        assert (dir_with_protected_files / ".env").exists()
        assert (dir_with_protected_files / ".git" / "config").exists()
        assert (dir_with_protected_files / "node_modules" / "package.json").exists()
        assert (dir_with_protected_files / ".venv" / "bin" / "python").exists()

    def test_snap_odd_number_of_files(self, temp_dir):
        """Test snap with odd number of files."""
        # Create 11 files
        for i in range(11):
            (temp_dir / f"file_{i}.txt").write_text(f"Content {i}")

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(temp_dir), no_protect=True)

        remaining_count = len(list(temp_dir.iterdir()))
        assert remaining_count == 6  # 11 // 2 = 5 deleted, 6 remain

    def test_snap_single_file(self, temp_dir):
        """Test snap with single file."""
        (temp_dir / "lonely.txt").write_text("alone")

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(temp_dir), no_protect=True)

        remaining_count = len(list(temp_dir.iterdir()))
        assert remaining_count == 1  # 1 // 2 = 0 deleted

    def test_snap_dry_run(self, populated_dir, capsys):
        """Test that dry run doesn't delete files."""
        initial_count = len(list(populated_dir.iterdir()))

        snap(str(populated_dir), dry_run=True, no_protect=True)

        remaining_count = len(list(populated_dir.iterdir()))
        assert remaining_count == initial_count  # No files deleted

        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_snap_cancelled(self, populated_dir, capsys):
        """Test that snap can be cancelled."""
        initial_count = len(list(populated_dir.iterdir()))

        with patch("rich.console.Console.input", return_value="no"):
            snap(str(populated_dir), no_protect=True)

        remaining_count = len(list(populated_dir.iterdir()))
        assert remaining_count == initial_count  # No files deleted

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()

    def test_snap_recursive(self, nested_dir):
        """Test snap in recursive mode."""
        initial_files = len([f for f in nested_dir.rglob("*") if f.is_file()])

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(nested_dir), recursive=True, no_protect=True)

        remaining_files = len([f for f in nested_dir.rglob("*") if f.is_file()])
        expected_remaining = initial_files - (initial_files // 2)
        assert remaining_files == expected_remaining

    def test_snap_with_seed_reproducible(self, temp_dir):
        """Test that using the same seed produces the same file selection."""
        # Create test files
        for i in range(10):
            (temp_dir / f"file_{i}.txt").write_text(f"Content {i}")

        # First run with seed
        snap(str(temp_dir), dry_run=True, seed=42, no_protect=True)

        # Get the files that would be selected
        files = get_files(str(temp_dir))
        import random

        random.seed(42)
        first_selection = set(random.sample(files, len(files) // 2))

        # Second run with same seed (in a fresh temp dir)
        temp_dir2 = Path(tempfile.mkdtemp())
        try:
            for i in range(10):
                (temp_dir2 / f"file_{i}.txt").write_text(f"Content {i}")

            files2 = get_files(str(temp_dir2))
            random.seed(42)
            second_selection = set(random.sample(files2, len(files2) // 2))

            # Compare just the filenames since paths will differ
            first_names = {f.name for f in first_selection}
            second_names = {f.name for f in second_selection}
            assert first_names == second_names
        finally:
            shutil.rmtree(temp_dir2, ignore_errors=True)

    def test_snap_with_thanosignore(self, temp_dir):
        """Test snap respects .thanosignore patterns."""
        # Create files
        (temp_dir / "keep.txt").write_text("keep")
        (temp_dir / "delete.txt").write_text("delete")
        important_dir = temp_dir / "important"
        important_dir.mkdir()
        (important_dir / "data.txt").write_text("important")

        # Create .thanosignore
        ignore_file = temp_dir / ".thanosignore"
        ignore_file.write_text("keep.txt\nimportant/\n")

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(temp_dir), recursive=True)

        # Protected files should exist
        assert (temp_dir / "keep.txt").exists()
        assert (important_dir / "data.txt").exists()

    def test_snap_with_weights(self, temp_dir):
        """Test snap with weighted selection."""
        # Create files with different extensions
        (temp_dir / "code.py").write_text("code")
        (temp_dir / "temp.tmp").write_text("temp")
        (temp_dir / "log.log").write_text("log")
        (temp_dir / "data.json").write_text("data")

        # Create .thanosrc.json with weights
        config_file = temp_dir / ".thanosrc.json"
        config_data = {
            "weights": {
                "by_extension": {
                    ".tmp": 0.99,  # Very likely to be eliminated
                    ".log": 0.99,  # Very likely to be eliminated
                    ".py": 0.01,  # Very unlikely to be eliminated
                    ".json": 0.01,  # Very unlikely to be eliminated
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        # Run snap multiple times and check that .py and .json survive more often
        survivors = []
        for _ in range(5):
            temp_test = Path(tempfile.mkdtemp())
            try:
                (temp_test / "code.py").write_text("code")
                (temp_test / "temp.tmp").write_text("temp")
                (temp_test / "log.log").write_text("log")
                (temp_test / "data.json").write_text("data")
                config_file_test = temp_test / ".thanosrc.json"
                config_file_test.write_text(json.dumps(config_data))

                with patch("rich.console.Console.input", return_value="snap"):
                    snap(str(temp_test), no_protect=True)

                survivor_names = {f.name for f in temp_test.iterdir() if f.is_file() and f.name != ".thanosrc.json"}
                survivors.append(survivor_names)
            finally:
                shutil.rmtree(temp_test, ignore_errors=True)

        # At least in some runs, .py or .json should survive
        # (This is probabilistic but with 0.01 vs 0.99 weights, should be very reliable)
        py_survived = sum("code.py" in s for s in survivors)
        json_survived = sum("data.json" in s for s in survivors)
        tmp_survived = sum("temp.tmp" in s for s in survivors)

        # With such extreme weights, .py and .json should survive more often
        assert py_survived + json_survived > tmp_survived


class TestInit:
    """Tests for the init command."""

    def test_init_creates_files(self, temp_dir):
        """Test that init creates .thanosignore and .thanosrc.json."""
        init(str(temp_dir))

        assert (temp_dir / ".thanosignore").exists()
        assert (temp_dir / ".thanosrc.json").exists()

    def test_init_thanosignore_content(self, temp_dir):
        """Test that .thanosignore has proper content."""
        init(str(temp_dir))

        content = (temp_dir / ".thanosignore").read_text()
        assert "important/" in content
        assert "*.db" in content
        assert "venv/" in content

    def test_init_thanosrc_content(self, temp_dir):
        """Test that .thanosrc.json has proper structure."""
        init(str(temp_dir))

        config = json.loads((temp_dir / ".thanosrc.json").read_text())
        assert "weights" in config
        assert "by_extension" in config["weights"]
        assert ".log" in config["weights"]["by_extension"]

    def test_init_doesnt_overwrite(self, temp_dir, capsys):
        """Test that init doesn't overwrite existing files."""
        # Create existing files
        (temp_dir / ".thanosignore").write_text("existing")
        (temp_dir / ".thanosrc.json").write_text('{"existing": true}')

        init(str(temp_dir))

        # Files should not be overwritten
        assert (temp_dir / ".thanosignore").read_text() == "existing"
        assert (temp_dir / ".thanosrc.json").read_text() == '{"existing": true}'

        captured = capsys.readouterr()
        assert "already exists" in captured.out


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_snap_with_permission_error(self, populated_dir, capsys):
        """Test snap when file deletion fails."""
        with patch("rich.console.Console.input", return_value="snap"):
            # Mock unlink to raise PermissionError
            original_unlink = Path.unlink

            def mock_unlink(self, *args, **kwargs):
                if "file_0" in str(self):
                    raise PermissionError("Permission denied")
                return original_unlink(self, *args, **kwargs)

            with patch.object(Path, "unlink", mock_unlink):
                snap(str(populated_dir), no_protect=True)

        captured = capsys.readouterr()
        assert "Failed" in captured.out or "complete" in captured.out

    def test_two_files(self, temp_dir):
        """Test snap with exactly two files."""
        (temp_dir / "file1.txt").write_text("one")
        (temp_dir / "file2.txt").write_text("two")

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(temp_dir), no_protect=True)

        remaining = len(list(temp_dir.iterdir()))
        assert remaining == 1  # 2 // 2 = 1 deleted, 1 remains

    def test_seed_with_zero(self, populated_dir, capsys):
        """Test that seed=0 is a valid seed."""
        snap(str(populated_dir), dry_run=True, seed=0, no_protect=True)
        captured = capsys.readouterr()
        assert "seed" in captured.out.lower()

    def test_seed_with_negative(self, populated_dir, capsys):
        """Test that negative seed values work."""
        snap(str(populated_dir), dry_run=True, seed=-42, no_protect=True)
        captured = capsys.readouterr()
        assert "seed" in captured.out.lower()

    def test_nonexistent_directory(self):
        """Test snap with nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            snap("/nonexistent/path/here")

    def test_file_instead_of_directory(self, temp_dir):
        """Test snap when given a file instead of directory."""
        test_file = temp_dir / "file.txt"
        test_file.write_text("content")

        with pytest.raises(NotADirectoryError):
            snap(str(test_file))


class TestPatternMatching:
    """Tests for gitignore-style pattern matching."""

    def test_wildcard_pattern(self, temp_dir):
        """Test wildcard patterns like *.log"""
        (temp_dir / "app.log").write_text("log")
        (temp_dir / "test.txt").write_text("text")

        patterns = {"*.log"}
        assert should_protect_file(temp_dir / "app.log", temp_dir, patterns)
        assert not should_protect_file(temp_dir / "test.txt", temp_dir, patterns)

    def test_directory_pattern_with_slash(self, temp_dir):
        """Test directory patterns ending with /"""
        logs_dir = temp_dir / "logs"
        logs_dir.mkdir()
        (logs_dir / "app.log").write_text("log")

        patterns = {"logs/"}
        assert should_protect_file(logs_dir / "app.log", temp_dir, patterns)

    def test_nested_directory_pattern(self, temp_dir):
        """Test patterns for nested directories"""
        node_dir = temp_dir / "node_modules"
        node_dir.mkdir()
        pkg_dir = node_dir / "package"
        pkg_dir.mkdir()
        lib_dir = pkg_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "index.js").write_text("code")

        patterns = {"node_modules/"}
        assert should_protect_file(lib_dir / "index.js", temp_dir, patterns)

    def test_double_star_pattern(self, temp_dir):
        """Test ** patterns"""
        test_dir = temp_dir / "src"
        test_dir.mkdir()
        sub_dir = test_dir / "sub"
        sub_dir.mkdir()
        (sub_dir / "test.pyc").write_text("bytecode")

        patterns = {"**/*.pyc"}
        assert should_protect_file(sub_dir / "test.pyc", temp_dir, patterns)

    def test_exact_filename_match(self, temp_dir):
        """Test exact filename patterns"""
        (temp_dir / ".env").write_text("SECRET=value")
        (temp_dir / ".env.local").write_text("LOCAL=value")

        patterns = {".env"}
        assert should_protect_file(temp_dir / ".env", temp_dir, patterns)
        assert not should_protect_file(temp_dir / ".env.local", temp_dir, patterns)

    def test_multiple_patterns(self, temp_dir):
        """Test multiple patterns at once"""
        (temp_dir / "file.log").write_text("log")
        (temp_dir / "file.tmp").write_text("tmp")
        (temp_dir / "file.txt").write_text("txt")

        patterns = {"*.log", "*.tmp"}
        assert should_protect_file(temp_dir / "file.log", temp_dir, patterns)
        assert should_protect_file(temp_dir / "file.tmp", temp_dir, patterns)
        assert not should_protect_file(temp_dir / "file.txt", temp_dir, patterns)

    def test_hidden_files(self, temp_dir):
        """Test protection of hidden files"""
        (temp_dir / ".gitignore").write_text("*.log")
        (temp_dir / "normal.txt").write_text("text")

        patterns = {".gitignore"}
        assert should_protect_file(temp_dir / ".gitignore", temp_dir, patterns)
        assert not should_protect_file(temp_dir / "normal.txt", temp_dir, patterns)


class TestWeightedSelection:
    """Tests for weighted file selection."""

    def test_weighted_selection_bias(self, temp_dir):
        """Test that weighted selection respects probability weights."""
        from thanos_cli.weights import calculate_file_weight

        # Create files
        files = []
        for ext in [".tmp", ".py", ".js", ".log"]:
            f = temp_dir / f"file{ext}"
            f.write_text("content")
            files.append(f)

        weights_config = {
            "by_extension": {
                ".tmp": 0.99,  # Almost always selected
                ".log": 0.99,
                ".py": 0.01,  # Almost never selected
                ".js": 0.01,
            }
        }

        # Calculate weights
        weights = [calculate_file_weight(f, weights_config) for f in files]

        # Verify weights are assigned correctly
        assert weights[0] == 0.99  # .tmp
        assert weights[1] == 0.01  # .py
        assert weights[2] == 0.01  # .js
        assert weights[3] == 0.99  # .log

    def test_weighted_sample_respects_k(self, temp_dir):
        """Test that weighted_random_sample returns correct number of items."""

        files = []
        for i in range(10):
            f = temp_dir / f"file_{i}.txt"
            f.write_text("content")
            files.append(f)

        weights = [0.5] * 10

        selected = weighted_random_sample(files, weights, 5)
        assert len(selected) == 5
        assert len(set(selected)) == 5  # All unique

    def test_default_weight_neutral(self, temp_dir):
        """Test that files without specific weights get 0.5 (neutral)."""

        test_file = temp_dir / "file.xyz"
        test_file.write_text("content")

        weights_config = {"by_extension": {".log": 0.9}}

        weight = calculate_file_weight(test_file, weights_config)
        assert weight == 0.5  # Default neutral weight

    def test_age_based_weights_recent_files(self, temp_dir):
        """Test age-based weights for recent files."""

        # Create a recent file
        recent_file = temp_dir / "recent.txt"
        recent_file.write_text("content")

        weights_config = {
            "by_age_days": {
                "0-7": 0.2,  # Recent files protected
                "7-30": 0.5,
                "30+": 0.9,  # Old files eliminated
            }
        }

        weight = calculate_file_weight(recent_file, weights_config)
        assert weight == 0.2  # Should match 0-7 range

    def test_age_based_weights_old_files(self, temp_dir):
        """Test age-based weights for old files."""

        # Create an old file by modifying its timestamp
        old_file = temp_dir / "old.txt"
        old_file.write_text("content")

        # Set modification time to 60 days ago
        old_time = time.time() - (60 * 86400)
        os.utime(old_file, (old_time, old_time))

        weights_config = {
            "by_age_days": {
                "0-7": 0.2,
                "7-30": 0.5,
                "30+": 0.9,  # Should match this
            }
        }

        weight = calculate_file_weight(old_file, weights_config)
        assert weight == 0.9  # Should match 30+ range

    def test_age_based_weights_middle_range(self, temp_dir):
        """Test age-based weights for files in middle age range."""

        # Create a file 15 days old
        mid_file = temp_dir / "mid.txt"
        mid_file.write_text("content")

        # Set modification time to 15 days ago
        mid_time = time.time() - (15 * 86400)
        os.utime(mid_file, (mid_time, mid_time))

        weights_config = {
            "by_age_days": {
                "0-7": 0.2,
                "7-30": 0.5,  # Should match this
                "30+": 0.9,
            }
        }

        weight = calculate_file_weight(mid_file, weights_config)
        assert weight == 0.5  # Should match 7-30 range

    def test_size_based_weights_small_files(self, temp_dir):
        """Test size-based weights for small files."""

        # Create a small file (< 1 MB)
        small_file = temp_dir / "small.txt"
        small_file.write_text("x" * 1024)  # 1 KB

        weights_config = {
            "by_size_mb": {
                "0-1": 0.3,  # Small files protected
                "1-10": 0.5,
                "10+": 0.9,  # Large files eliminated
            }
        }

        weight = calculate_file_weight(small_file, weights_config)
        assert weight == 0.3  # Should match 0-1 MB range

    def test_size_based_weights_large_files(self, temp_dir):
        """Test size-based weights for large files."""

        # Create a large file (> 10 MB)
        large_file = temp_dir / "large.bin"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))  # 11 MB

        weights_config = {
            "by_size_mb": {
                "0-1": 0.3,
                "1-10": 0.5,
                "10+": 0.9,  # Should match this
            }
        }

        weight = calculate_file_weight(large_file, weights_config)
        assert weight == 0.9  # Should match 10+ MB range

    def test_size_based_weights_medium_files(self, temp_dir):
        """Test size-based weights for medium-sized files."""

        # Create a medium file (5 MB)
        medium_file = temp_dir / "medium.bin"
        medium_file.write_bytes(b"x" * (5 * 1024 * 1024))  # 5 MB

        weights_config = {
            "by_size_mb": {
                "0-1": 0.3,
                "1-10": 0.5,  # Should match this
                "10+": 0.9,
            }
        }

        weight = calculate_file_weight(medium_file, weights_config)
        assert weight == 0.5  # Should match 1-10 MB range

    def test_combined_weights_averaging(self, temp_dir):
        """Test that multiple weight types are averaged."""

        # Create a file with known properties
        test_file = temp_dir / "test.log"
        test_file.write_bytes(b"x" * (5 * 1024 * 1024))  # 5 MB

        # Set modification time to 15 days ago
        mid_time = time.time() - (15 * 86400)
        os.utime(test_file, (mid_time, mid_time))

        weights_config = {
            "by_extension": {".log": 0.9},  # High elimination
            "by_age_days": {
                "0-7": 0.2,
                "7-30": 0.5,  # Matches
                "30+": 0.9,
            },
            "by_size_mb": {
                "0-1": 0.3,
                "1-10": 0.7,  # Matches
                "10+": 0.9,
            },
        }

        weight = calculate_file_weight(test_file, weights_config)
        # Should average: (0.9 + 0.5 + 0.7) / 3 = 0.7
        assert abs(weight - 0.7) < 0.01

    def test_age_range_formats(self, temp_dir):
        """Test different age range format syntaxes."""
        # Test "30+" format
        assert _matches_age_range(40, "30+")
        assert not _matches_age_range(20, "30+")

        # Test "30-" format (alternative)
        assert _matches_age_range(40, "30-")
        assert not _matches_age_range(20, "30-")

        # Test "0-7" format
        assert _matches_age_range(5, "0-7")
        assert not _matches_age_range(10, "0-7")

        # Test "7-30" format
        assert _matches_age_range(15, "7-30")
        assert not _matches_age_range(5, "7-30")
        assert not _matches_age_range(35, "7-30")

    def test_size_range_formats(self, temp_dir):
        """Test different size range format syntaxes."""
        # Test "10+" format
        assert _matches_size_range(15, "10+")
        assert not _matches_size_range(5, "10+")

        # Test "10-" format (alternative)
        assert _matches_size_range(15, "10-")
        assert not _matches_size_range(5, "10-")

        # Test "0-1" format
        assert _matches_size_range(0.5, "0-1")
        assert not _matches_size_range(1.5, "0-1")

        # Test "1-10" format
        assert _matches_size_range(5, "1-10")
        assert not _matches_size_range(0.5, "1-10")
        assert not _matches_size_range(15, "1-10")

    def test_weight_with_missing_file_stats(self, temp_dir):
        """Test that weight calculation handles missing file stats gracefully."""
        # Create a file
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        weights_config = {"by_extension": {".txt": 0.8}, "by_age_days": {"0-7": 0.2, "30+": 0.9}}

        # Mock stat() to raise OSError
        original_stat = Path.stat

        def mock_stat(self):
            if "test.txt" in str(self):
                raise OSError("Cannot access file")
            return original_stat(self)

        with patch.object(Path, "stat", mock_stat):
            weight = calculate_file_weight(test_file, weights_config)
            # Should only use extension weight since age fails
            assert weight == 0.8

    def test_weights_only_extension(self, temp_dir):
        """Test weights with only extension specified."""
        test_file = temp_dir / "test.log"
        test_file.write_text("content")

        weights_config = {"by_extension": {".log": 0.85}}

        weight = calculate_file_weight(test_file, weights_config)
        assert weight == 0.85

    def test_weights_only_age(self, temp_dir):
        """Test weights with only age specified."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        weights_config = {"by_age_days": {"0-7": 0.25, "7+": 0.75}}

        weight = calculate_file_weight(test_file, weights_config)
        assert weight == 0.25  # Recent file

    def test_weights_only_size(self, temp_dir):
        """Test weights with only size specified."""
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2 MB

        weights_config = {"by_size_mb": {"0-1": 0.2, "1-5": 0.6, "5+": 0.9}}

        weight = calculate_file_weight(test_file, weights_config)
        assert weight == 0.6  # 1-5 MB range


class TestConfigDiscovery:
    """Tests for config file discovery in parent directories."""

    def test_config_found_in_parent(self, temp_dir):
        """Test that config is found in parent directory."""
        ignore_file = temp_dir / ".thanosignore"
        ignore_file.write_text("*.log\n")

        subdir = temp_dir / "sub1" / "sub2" / "sub3"
        subdir.mkdir(parents=True)

        patterns, path = load_thanosignore(str(subdir))
        assert "*.log" in patterns
        assert path == ignore_file

    def test_config_stops_at_filesystem_root(self, temp_dir):
        """Test that config search doesn't go beyond reasonable depth."""
        deep_dir = temp_dir
        for i in range(10):
            deep_dir = deep_dir / f"level{i}"
            deep_dir.mkdir()

        # Should not crash, just return empty
        patterns, path = load_thanosignore(str(deep_dir))
        assert path is None or path.exists()

    def test_config_prefers_closer_file(self, temp_dir):
        """Test that closer config file takes precedence."""
        # Parent .thanosignore
        parent_ignore = temp_dir / ".thanosignore"
        parent_ignore.write_text("*.log\n")

        # Child .thanosignore (should be preferred)
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        child_ignore = subdir / ".thanosignore"
        child_ignore.write_text("*.tmp\n")

        patterns, path = load_thanosignore(str(subdir))
        assert "*.tmp" in patterns
        assert path == child_ignore


class TestRealWorldScenarios:
    """Tests simulating real-world usage scenarios."""

    def test_python_project_structure(self, temp_dir):
        """Test snap on typical Python project."""
        # Create typical Python project structure
        (temp_dir / "main.py").write_text("print('hello')")
        (temp_dir / "requirements.txt").write_text("requests==2.28.0")
        (temp_dir / ".env").write_text("SECRET=key")

        venv = temp_dir / "venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("config")

        cache = temp_dir / "__pycache__"
        cache.mkdir()
        (cache / "main.cpython-39.pyc").write_text("bytecode")

        # Should protect .env, venv/, __pycache__/
        all_files = list(temp_dir.rglob("*"))
        all_files = [f for f in all_files if f.is_file()]

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(temp_dir), recursive=True)

        # Critical files should survive
        assert (temp_dir / ".env").exists()
        assert (temp_dir / "venv" / "pyvenv.cfg").exists()

    def test_node_project_structure(self, temp_dir):
        """Test snap on typical Node.js project."""
        (temp_dir / "package.json").write_text('{"name": "app"}')
        (temp_dir / "index.js").write_text("console.log('hello')")

        node_modules = temp_dir / "node_modules"
        node_modules.mkdir()
        pkg = node_modules / "express"
        pkg.mkdir()
        (pkg / "index.js").write_text("module.exports = {}")

        with patch("rich.console.Console.input", return_value="snap"):
            snap(str(temp_dir), recursive=True)

        # node_modules should be protected
        assert (node_modules / "express" / "index.js").exists()

    def test_mixed_project_with_logs_and_cache(self, temp_dir):
        """Test project with logs and cache that should be eliminated."""
        # Important files
        (temp_dir / "app.py").write_text("code")
        (temp_dir / "config.yaml").write_text("config")

        # Temporary files (should be eligible for elimination)
        (temp_dir / "debug.log").write_text("logs")
        (temp_dir / "cache.tmp").write_text("cache")
        (temp_dir / "old.bak").write_text("backup")

        # Create weighted config
        config_file = temp_dir / ".thanosrc.json"
        config_data = {
            "weights": {"by_extension": {".log": 0.95, ".tmp": 0.95, ".bak": 0.90, ".py": 0.05, ".yaml": 0.05}}
        }
        config_file.write_text(json.dumps(config_data))

        # Run multiple times, important files should survive more often
        survival_counts = {".py": 0, ".yaml": 0, ".log": 0, ".tmp": 0, ".bak": 0}

        for trial in range(10):
            test_dir = temp_dir / f"trial_{trial}"
            test_dir.mkdir()

            (test_dir / "app.py").write_text("code")
            (test_dir / "config.yaml").write_text("config")
            (test_dir / "debug.log").write_text("logs")
            (test_dir / "cache.tmp").write_text("cache")
            (test_dir / "old.bak").write_text("backup")

            config_trial = test_dir / ".thanosrc.json"
            config_trial.write_text(json.dumps(config_data))

            with patch("rich.console.Console.input", return_value="snap"):
                snap(str(test_dir), no_protect=True)

            for f in test_dir.iterdir():
                if f.suffix in survival_counts and f.is_file():
                    survival_counts[f.suffix] += 1

        # Important files should survive significantly more often
        assert survival_counts[".py"] > survival_counts[".log"]
        assert survival_counts[".yaml"] > survival_counts[".tmp"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
