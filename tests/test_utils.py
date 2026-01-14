"""Tests for utils module functionality."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetDataDirectory(unittest.TestCase):
    """Test cases for get_data_directory function."""

    def test_returns_path_object(self):
        """Test that function returns a Path object."""
        from activity_tracker.utils import get_data_directory

        result = get_data_directory()
        self.assertIsInstance(result, Path)

    @patch("sys.platform", "darwin")
    def test_returns_macos_path_on_darwin(self):
        """Test macOS-specific path on darwin platform."""
        from activity_tracker.utils import get_data_directory

        result = get_data_directory()
        self.assertIn("Library", str(result))
        self.assertIn("Application Support", str(result))
        self.assertIn("ActivityTracker", str(result))

    def test_directory_exists_after_call(self):
        """Test that directory is created if it doesn't exist."""
        from activity_tracker.utils import get_data_directory

        result = get_data_directory()
        self.assertTrue(result.exists())


class TestViewActivityFile(unittest.TestCase):
    """Test cases for view_activity_file function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_view_valid_activity_file(self):
        """Test viewing a valid activity file."""
        # Create a test file
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        test_data = {"App1": 30.5, "App2": 25.0}
        with open(filepath, "w") as f:
            json.dump(test_data, f)

        from activity_tracker.utils import view_activity_file

        # Should not raise any exceptions
        with patch("builtins.print"):
            view_activity_file(str(filepath))

    def test_view_file_with_unicode(self):
        """Test viewing file with Unicode characters."""
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        test_data = {"App — Test": 30.5, "App • Demo": 25.0}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)

        from activity_tracker.utils import view_activity_file

        with patch("builtins.print"):
            view_activity_file(str(filepath))

    def test_view_invalid_json_file(self):
        """Test viewing invalid JSON file."""
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        with open(filepath, "w") as f:
            f.write("not valid json")

        from activity_tracker.utils import view_activity_file

        with patch("builtins.print") as mock_print:
            view_activity_file(str(filepath))
            # Should print error message
            calls = [str(call) for call in mock_print.call_args_list]
            error_printed = any("[ERROR]" in str(call) for call in calls)
            self.assertTrue(error_printed)

    def test_view_nonexistent_file(self):
        """Test viewing non-existent file."""
        filepath = Path(self.temp_dir) / "nonexistent.json"

        from activity_tracker.utils import view_activity_file

        with patch("builtins.print"):
            # Should handle gracefully
            view_activity_file(str(filepath))


class TestViewActivityFileParsing(unittest.TestCase):
    """Test cases for filename parsing in view_activity_file."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_parses_standard_filename(self):
        """Test parsing standard activity filename."""
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        with open(filepath, "w") as f:
            json.dump({"App1": 30.0}, f)

        from activity_tracker.utils import view_activity_file

        with patch("builtins.print") as mock_print:
            view_activity_file(str(filepath))
            # Should print date in formatted form
            calls = str(mock_print.call_args_list)
            self.assertIn("2024-01-15", calls)

    def test_handles_non_standard_filename(self):
        """Test handling non-standard filename."""
        filepath = Path(self.temp_dir) / "custom_file.json"
        with open(filepath, "w") as f:
            json.dump({"App1": 30.0}, f)

        from activity_tracker.utils import view_activity_file

        with patch("builtins.print"):
            # Should not raise exception
            view_activity_file(str(filepath))


class TestUtilsMain(unittest.TestCase):
    """Test cases for utils main function."""

    def test_main_shows_usage_with_no_args(self):
        """Test main shows usage when no arguments provided."""
        from activity_tracker.utils import main

        with patch("sys.argv", ["utils.py"]):
            with patch("builtins.print") as mock_print:
                main()
                calls = str(mock_print.call_args_list)
                self.assertIn("Usage", calls)

    def test_main_handles_nonexistent_file(self):
        """Test main handles nonexistent file gracefully."""
        from activity_tracker.utils import main

        with patch("sys.argv", ["utils.py", "/nonexistent/file.json"]):
            with patch("builtins.print") as mock_print:
                main()
                calls = str(mock_print.call_args_list)
                self.assertIn("[ERROR]", calls)


if __name__ == "__main__":
    unittest.main()
