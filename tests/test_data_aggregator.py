"""Tests for data_aggregator module functionality."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


class TestActivityFileParser(unittest.TestCase):
    """Test cases for ActivityFileParser class."""

    def setUp(self):
        """Set up test fixtures."""
        from activity_tracker.data_aggregator import ActivityFileParser
        self.parser = ActivityFileParser()

    def test_parse_filename_valid(self):
        """Test parsing valid activity filename."""
        result = self.parser.parse_filename("activity_20240115_1430.json")

        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_parse_filename_invalid(self):
        """Test parsing invalid activity filename."""
        result = self.parser.parse_filename("invalid_filename.json")
        self.assertIsNone(result)

    def test_parse_filename_wrong_format(self):
        """Test parsing wrong format filename."""
        result = self.parser.parse_filename("activity_2024-01-15_1430.json")
        self.assertIsNone(result)

    def test_get_hour_key(self):
        """Test getting hour key from datetime."""
        dt = datetime(2024, 1, 15, 14, 30)
        result = self.parser.get_hour_key(dt)
        self.assertEqual(result, "2024-01-15_14")


class TestDataAggregator(unittest.TestCase):
    """Test cases for DataAggregator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        from activity_tracker.data_aggregator import DataAggregator
        self.aggregator = DataAggregator(data_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test DataAggregator initialization."""
        self.assertEqual(self.aggregator.data_dir, Path(self.temp_dir))

    def test_group_files_by_hour_empty_dir(self):
        """Test grouping files in empty directory."""
        result = self.aggregator.group_files_by_hour()
        self.assertEqual(result, {})

    def test_group_files_by_hour(self):
        """Test grouping activity files by hour."""
        # Create test files
        files = [
            ("activity_20240115_1430.json", {"App1": 30.0}),
            ("activity_20240115_1431.json", {"App2": 25.0}),
            ("activity_20240115_1530.json", {"App3": 45.0}),
        ]

        for filename, data in files:
            filepath = Path(self.temp_dir) / filename
            with open(filepath, "w") as f:
                json.dump(data, f)

        result = self.aggregator.group_files_by_hour()

        self.assertEqual(len(result), 2)  # Two different hours
        self.assertIn("2024-01-15_14", result)
        self.assertIn("2024-01-15_15", result)
        self.assertEqual(len(result["2024-01-15_14"]), 2)
        self.assertEqual(len(result["2024-01-15_15"]), 1)

    def test_aggregate_hour_data(self):
        """Test aggregating data from multiple files."""
        # Create test files
        files = [
            ("activity_20240115_1430.json", {"App1": 30.0, "App2": 20.0}),
            ("activity_20240115_1431.json", {"App1": 15.0, "App2": 35.0}),
        ]

        file_paths = []
        for filename, data in files:
            filepath = Path(self.temp_dir) / filename
            with open(filepath, "w") as f:
                json.dump(data, f)
            file_paths.append(filepath)

        result = self.aggregator.aggregate_hour_data(file_paths)

        self.assertEqual(result["applications"]["App1"], 45.0)
        self.assertEqual(result["applications"]["App2"], 55.0)
        self.assertEqual(result["total_time"], 100.0)
        self.assertEqual(result["files_processed"], 2)

    def test_aggregate_hour_data_handles_corrupt_file(self):
        """Test aggregation handles corrupt files gracefully."""
        # Create a valid file
        valid_path = Path(self.temp_dir) / "activity_20240115_1430.json"
        with open(valid_path, "w") as f:
            json.dump({"App1": 30.0}, f)

        # Create a corrupt file
        corrupt_path = Path(self.temp_dir) / "activity_20240115_1431.json"
        with open(corrupt_path, "w") as f:
            f.write("not valid json")

        with patch("builtins.print"):
            result = self.aggregator.aggregate_hour_data([valid_path, corrupt_path])

        # Should still aggregate valid file
        self.assertEqual(result["applications"]["App1"], 30.0)
        self.assertEqual(result["files_processed"], 1)


class TestSyncStateManager(unittest.TestCase):
    """Test cases for SyncStateManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        from activity_tracker.data_aggregator import SyncStateManager
        self.manager = SyncStateManager(data_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test SyncStateManager initialization."""
        self.assertEqual(self.manager.synced_hours, set())

    def test_is_hour_synced_false_when_not_synced(self):
        """Test is_hour_synced returns False for unsynced hour."""
        result = self.manager.is_hour_synced("2024-01-15_14")
        self.assertFalse(result)

    def test_mark_hour_synced(self):
        """Test marking hour as synced."""
        self.manager.mark_hour_synced("2024-01-15_14")
        self.assertTrue(self.manager.is_hour_synced("2024-01-15_14"))

    def test_save_and_load_synced_hours(self):
        """Test saving and loading synced hours."""
        self.manager.mark_hour_synced("2024-01-15_14")
        self.manager.mark_hour_synced("2024-01-15_15")

        # Create a new manager instance
        from activity_tracker.data_aggregator import SyncStateManager
        new_manager = SyncStateManager(data_dir=self.temp_dir)

        self.assertTrue(new_manager.is_hour_synced("2024-01-15_14"))
        self.assertTrue(new_manager.is_hour_synced("2024-01-15_15"))

    def test_get_pending_hours(self):
        """Test getting pending (unsynced) hours."""
        self.manager.mark_hour_synced("2024-01-15_14")

        available_hours = ["2024-01-15_14", "2024-01-15_15", "2024-01-15_16"]
        result = self.manager.get_pending_hours(available_hours)

        self.assertEqual(len(result), 2)
        self.assertIn("2024-01-15_15", result)
        self.assertIn("2024-01-15_16", result)

    def test_get_sync_statistics(self):
        """Test getting sync statistics."""
        self.manager.mark_hour_synced("2024-01-15_14")

        available_hours = ["2024-01-15_14", "2024-01-15_15"]
        stats = self.manager.get_sync_statistics(available_hours)

        self.assertEqual(stats["total_hours"], 2)
        self.assertEqual(stats["synced_hours"], 1)
        self.assertEqual(stats["pending_hours"], 1)


if __name__ == "__main__":
    unittest.main()
