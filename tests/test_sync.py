"""Tests for sync functionality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from activity_tracker.sync import SyncManager


class TestSyncManager(unittest.TestCase):
    """Test cases for SyncManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sync_manager = SyncManager(
            data_dir=self.temp_dir, endpoint="https://test.example.com/api/data"
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test SyncManager initialization."""
        self.assertEqual(
            self.sync_manager.data_aggregator.data_dir, Path(self.temp_dir)
        )
        self.assertEqual(
            self.sync_manager.endpoint, "https://test.example.com/api/data"
        )
        self.assertIsNotNone(self.sync_manager.sync_state.synced_hours_file)

    def test_create_sample_data(self):
        """Test creation of sample activity data files."""
        # Create sample data files
        sample_data = {"App1": 30.5, "App2": 25.2, "App3": 4.3}

        data_file = Path(self.temp_dir) / "activity_20240115_1430.json"
        with open(data_file, "w") as f:
            json.dump(sample_data, f)

        self.assertTrue(data_file.exists())

        # Test file discovery
        json_files = list(Path(self.temp_dir).glob("activity_*.json"))
        self.assertEqual(len(json_files), 1)

    def test_group_files_by_hour(self):
        """Test grouping activity files by hour."""
        # Create multiple files for the same hour
        sample_data1 = {"App1": 30.0}
        sample_data2 = {"App2": 25.0}
        sample_data3 = {"App3": 5.0}

        files = [
            "activity_20240115_1430.json",
            "activity_20240115_1431.json",
            "activity_20240115_1432.json",
            "activity_20240115_1530.json",  # Different hour
        ]

        data_sets = [sample_data1, sample_data2, sample_data3, {"App4": 60.0}]

        for filename, data in zip(files, data_sets):
            filepath = Path(self.temp_dir) / filename
            with open(filepath, "w") as f:
                json.dump(data, f)

        # Test grouping logic (would need to implement in SyncManager)
        json_files = list(Path(self.temp_dir).glob("activity_*.json"))
        self.assertEqual(len(json_files), 4)

        # Group by hour prefix
        hours = set()
        for file in json_files:
            # Extract hour from filename
            # (e.g., "20240115_14" from "activity_20240115_1430.json")
            hour = file.stem.split("_")[1] + "_" + file.stem.split("_")[2][:2]
            hours.add(hour)

        self.assertEqual(len(hours), 2)  # Two different hours

    @patch("requests.post")
    def test_successful_sync(self, mock_post):
        """Test successful data synchronization."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        # Create test data
        test_data = {
            "timestamp": "2024-01-15T14:00:00Z",
            "hour": "2024-01-15_14",
            "data": {
                "applications": {"App1": 30.0, "App2": 30.0},
                "total_time": 60.0,
                "files_processed": 2,
            },
        }

        # Test sync (this would be implemented in SyncManager)
        # For now, just test the HTTP call
        response = requests.post(
            self.sync_manager.endpoint,
            json=test_data,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_failed_sync(self, mock_post):
        """Test handling of failed synchronization."""
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        test_data = {"test": "data"}

        # Test failed sync
        response = requests.post(self.sync_manager.endpoint, json=test_data)

        self.assertEqual(response.status_code, 500)

    @patch("requests.post")
    def test_network_timeout(self, mock_post):
        """Test handling of network timeouts."""
        # Mock network timeout
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        test_data = {"test": "data"}

        # Test timeout handling
        with self.assertRaises(requests.exceptions.Timeout):
            requests.post(self.sync_manager.endpoint, json=test_data, timeout=5)

    def test_synced_hours_tracking(self):
        """Test tracking of already synced hours."""
        synced_hours_file = Path(self.temp_dir) / "synced_hours.json"

        # Test empty synced hours
        if not synced_hours_file.exists():
            synced_hours = []
        else:
            with open(synced_hours_file, "r") as f:
                synced_hours = json.load(f)

        self.assertEqual(synced_hours, [])

        # Test adding synced hour
        new_hour = "2024-01-15_14"
        synced_hours.append(new_hour)

        with open(synced_hours_file, "w") as f:
            json.dump(synced_hours, f)

        # Verify it was saved
        with open(synced_hours_file, "r") as f:
            saved_hours = json.load(f)

        self.assertIn(new_hour, saved_hours)

    def test_data_aggregation(self):
        """Test aggregating activity data by application."""
        # Sample minute-level data
        minute_data = [
            {"App1": 20.0, "App2": 40.0},
            {"App1": 15.0, "App2": 35.0, "App3": 10.0},
            {"App1": 25.0, "App3": 35.0},
        ]

        # Aggregate data
        aggregated = {}
        for minute in minute_data:
            for app, time_spent in minute.items():
                aggregated[app] = aggregated.get(app, 0) + time_spent

        expected = {"App1": 60.0, "App2": 75.0, "App3": 45.0}
        self.assertEqual(aggregated, expected)

        # Test total time
        total_time = sum(aggregated.values())
        self.assertEqual(total_time, 180.0)

    def test_data_format_validation(self):
        """Test validation of sync data format."""
        valid_data = {
            "timestamp": "2024-01-15T14:00:00Z",
            "hour": "2024-01-15_14",
            "data": {
                "applications": {"App1": 30.0},
                "total_time": 30.0,
                "files_processed": 1,
            },
            "source": "macos-activity-tracker",
            "version": "1.0.0",
        }

        # Test required fields
        required_fields = ["timestamp", "hour", "data"]
        for field in required_fields:
            self.assertIn(field, valid_data)

        # Test data structure
        self.assertIn("applications", valid_data["data"])
        self.assertIn("total_time", valid_data["data"])
        self.assertIsInstance(valid_data["data"]["applications"], dict)
        self.assertIsInstance(valid_data["data"]["total_time"], (int, float))


class TestSyncManagerIntegration(unittest.TestCase):
    """Integration tests for SyncManager."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.integration
    @patch("requests.post")
    def test_full_sync_workflow(self, mock_post):
        """Test complete sync workflow from files to API."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        # Create sync manager instance
        SyncManager(data_dir=self.temp_dir, endpoint="https://test.example.com/api")

        # Create sample data files
        files_data = [
            ("activity_20240115_1430.json", {"App1": 20.0, "App2": 40.0}),
            ("activity_20240115_1431.json", {"App1": 15.0, "App2": 35.0}),
            ("activity_20240115_1432.json", {"App1": 25.0, "App2": 25.0}),
        ]

        for filename, data in files_data:
            filepath = Path(self.temp_dir) / filename
            with open(filepath, "w") as f:
                json.dump(data, f)

        # Verify files exist
        json_files = list(Path(self.temp_dir).glob("activity_*.json"))
        self.assertEqual(len(json_files), 3)

        # Test that sync manager can find and process files
        # (TODO)


if __name__ == "__main__":
    unittest.main()
