#!/usr/bin/env python

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import thanos
from thanos.cli import snap, main
from thanos.utils import get_files


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    # Cleanup
    shutil.rmtree(tmpdir)


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


class TestSnap:
    """Tests for the snap function."""

    def test_snap_empty_directory(self, temp_dir, capsys):
        """Test snap on empty directory."""
        snap(str(temp_dir))
        captured = capsys.readouterr()
        assert "No files found" in captured.out

    def test_snap_deletes_half_files(self, populated_dir):
        """Test that snap deletes approximately half the files."""
        initial_count = len(list(populated_dir.iterdir()))
        assert initial_count == 10

        with patch("builtins.input", return_value="snap"):
            snap(str(populated_dir))

        remaining_count = len(list(populated_dir.iterdir()))
        assert remaining_count == 5  # Half of 10

    def test_snap_odd_number_of_files(self, temp_dir):
        """Test snap with odd number of files."""
        # Create 11 files
        for i in range(11):
            (temp_dir / f"file_{i}.txt").write_text(f"Content {i}")

        with patch("builtins.input", return_value="snap"):
            snap(str(temp_dir))

        remaining_count = len(list(temp_dir.iterdir()))
        assert remaining_count == 6  # 11 // 2 = 5 deleted, 6 remain

    def test_snap_single_file(self, temp_dir):
        """Test snap with single file."""
        (temp_dir / "lonely.txt").write_text("alone")

        with patch("builtins.input", return_value="snap"):
            snap(str(temp_dir))

        remaining_count = len(list(temp_dir.iterdir()))
        assert remaining_count == 1  # 1 // 2 = 0 deleted

    def test_snap_dry_run(self, populated_dir, capsys):
        """Test that dry run doesn't delete files."""
        initial_count = len(list(populated_dir.iterdir()))

        snap(str(populated_dir), dry_run=True)

        remaining_count = len(list(populated_dir.iterdir()))
        assert remaining_count == initial_count  # No files deleted

        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "would be eliminated" in captured.out

    def test_snap_cancelled(self, populated_dir, capsys):
        """Test that snap can be cancelled."""
        initial_count = len(list(populated_dir.iterdir()))

        with patch("builtins.input", return_value="no"):
            snap(str(populated_dir))

        remaining_count = len(list(populated_dir.iterdir()))
        assert remaining_count == initial_count  # No files deleted

        captured = capsys.readouterr()
        assert "cancelled" in captured.out

    def test_snap_recursive(self, nested_dir):
        """Test snap in recursive mode."""
        initial_count = len(list(nested_dir.rglob("*")))
        initial_files = len([f for f in nested_dir.rglob("*") if f.is_file()])

        with patch("builtins.input", return_value="snap"):
            snap(str(nested_dir), recursive=True)

        remaining_files = len([f for f in nested_dir.rglob("*") if f.is_file()])
        expected_remaining = initial_files - (initial_files // 2)
        assert remaining_files == expected_remaining

    def test_snap_randomness(self, temp_dir):
        """Test that snap uses randomness in file selection."""
        # Create multiple test directories with identical files
        results = []

        for trial in range(3):
            trial_dir = temp_dir / f"trial_{trial}"
            trial_dir.mkdir()

            # Create 10 files
            for i in range(10):
                (trial_dir / f"file_{i}.txt").write_text(f"Content {i}")

            with patch("builtins.input", return_value="snap"):
                snap(str(trial_dir))

            # Record which files survived
            survivors = {f.name for f in trial_dir.iterdir()}
            results.append(survivors)

        # At least one trial should have different survivors
        # (extremely unlikely all three are identical with random selection)
        assert not all(r == results[0] for r in results)


class TestMain:
    """Tests for the main CLI function."""

    def test_main_with_dry_run(self, populated_dir, capsys):
        """Test main function with dry-run argument."""
        with patch("sys.argv", ["thanos", str(populated_dir), "--dry-run"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_main_with_recursive(self, nested_dir):
        """Test main function with recursive argument."""
        with patch("sys.argv", ["thanos", str(nested_dir), "-r", "-d"]):
            result = main()

        assert result == 0

    def test_main_with_nonexistent_dir(self, capsys):
        """Test main function with nonexistent directory."""
        with patch("sys.argv", ["thanos", "/fake/directory"]):
            result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_main_default_directory(self, temp_dir, capsys):
        """Test main function with default (current) directory."""
        # Change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create some files
            for i in range(4):
                (temp_dir / f"file_{i}.txt").write_text(f"Content {i}")

            with patch("sys.argv", ["thanos", "--dry-run"]):
                result = main

            assert result == 0
            captured = capsys.readouterr()
            assert "Total files: 4" in captured.out
        finally:
            os.chdir(original_dir)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_snap_with_permission_error(self, populated_dir, capsys):
        """Test snap when file deletion fails."""
        # Make one file read-only (on Unix systems)
        test_file = list(populated_dir.iterdir())[0]

        # Mock unlink to raise PermissionError for specific file
        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if self == test_file:
                raise PermissionError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        with patch("builtins.input", return_value="snap"):
            with patch.object(Path, "unlink", mock_unlink):
                snap(str(populated_dir))

        captured = capsys.readouterr()
        assert "Failed to eliminate" in captured.out or "snap is complete" in captured.out

    def test_two_files(self, temp_dir):
        """Test snap with exactly two files."""
        (temp_dir / "file1.txt").write_text("one")
        (temp_dir / "file2.txt").write_text("two")

        with patch("builtins.input", return_value="snap"):
            snap(str(temp_dir))

        remaining = len(list(temp_dir.iterdir()))
        assert remaining == 1  # 2 // 2 = 1 deleted, 1 remains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
