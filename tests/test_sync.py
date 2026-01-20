"""Tests for sync functionality."""

import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from activity_tracker.sync import SyncManager, main


class TestSyncManager(unittest.TestCase):
    """Test cases for SyncManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.endpoint = "https://test.example.com/api/data"
        self.sync_manager = SyncManager(
            data_dir=self.temp_dir, endpoint=self.endpoint, auth_token="token"
        )

        # Mock components
        self.sync_manager.data_aggregator = MagicMock()
        self.sync_manager.sync_state = MagicMock()
        self.sync_manager.http_client = MagicMock()
        self.sync_manager.device_identifier = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test SyncManager initialization."""
        manager = SyncManager(data_dir=self.temp_dir, endpoint="http://test")
        self.assertEqual(manager.endpoint, "http://test")
        self.assertIsNotNone(manager.data_aggregator)
        self.assertIsNotNone(manager.sync_state)
        self.assertIsNotNone(manager.http_client)

    def test_sync_hour_no_endpoint(self):
        """Test sync_hour fails gracefully without endpoint."""
        self.sync_manager.endpoint = ""
        with patch("builtins.print") as mock_print:
            result = self.sync_manager.sync_hour("2024-01-01_12", {})

        self.assertFalse(result)
        mock_print.assert_called_with("Error: No sync endpoint configured.")

    def test_sync_hour_already_synced(self):
        """Test sync_hour skips if already synced."""
        self.sync_manager.sync_state.is_hour_synced.return_value = True

        with patch("builtins.print") as mock_print:
            result = self.sync_manager.sync_hour("2024-01-01_12", {})

        self.assertTrue(result)
        self.sync_manager.http_client.sync_hour_data.assert_not_called()
        mock_print.assert_called()

    def test_sync_hour_force(self):
        """Test sync_hour proceeds if forced even if synced."""
        self.sync_manager.sync_state.is_hour_synced.return_value = True
        self.sync_manager.http_client.sync_hour_data.return_value = True

        result = self.sync_manager.sync_hour("2024-01-01_12", {}, force=True)

        self.assertTrue(result)
        self.sync_manager.http_client.sync_hour_data.assert_called()
        self.sync_manager.sync_state.mark_hour_synced.assert_called_with(
            "2024-01-01_12"
        )

    def test_sync_hour_success(self):
        """Test successful sync_hour."""
        self.sync_manager.sync_state.is_hour_synced.return_value = False
        self.sync_manager.http_client.sync_hour_data.return_value = True

        result = self.sync_manager.sync_hour("2024-01-01_12", {})

        self.assertTrue(result)
        self.sync_manager.sync_state.mark_hour_synced.assert_called_with(
            "2024-01-01_12"
        )

    def test_sync_hour_failure(self):
        """Test failed sync_hour."""
        self.sync_manager.sync_state.is_hour_synced.return_value = False
        self.sync_manager.http_client.sync_hour_data.return_value = False

        result = self.sync_manager.sync_hour("2024-01-01_12", {})

        self.assertFalse(result)
        self.sync_manager.sync_state.mark_hour_synced.assert_not_called()

    def test_sync_all_no_endpoint(self):
        """Test sync_all fails without endpoint."""
        self.sync_manager.endpoint = ""
        with patch("builtins.print") as mock_print:
            result = self.sync_manager.sync_all()

        self.assertEqual(result["synced"], 0)
        mock_print.assert_called()

    def test_sync_all_no_files(self):
        """Test sync_all with no files."""
        self.sync_manager.data_aggregator.group_files_by_hour.return_value = {}

        with patch("builtins.print") as mock_print:
            result = self.sync_manager.sync_all()

        self.assertEqual(result["synced"], 0)
        mock_print.assert_called_with("No activity files found to sync")

    def test_sync_all_mixed_results(self):
        """Test sync_all with mixed success/fail/skip."""
        files = {"h1": ["f1"], "h2": ["f2"], "h3": ["f3"]}
        self.sync_manager.data_aggregator.group_files_by_hour.return_value = files

        # h1: skip (already synced)
        # h2: success
        # h3: fail
        def is_synced(hour):
            return hour == "h1"

        self.sync_manager.sync_state.is_hour_synced.side_effect = is_synced

        # Mock sync_hour explicitly to control outcome for h2 and h3
        # Since sync_all calls sync_hour, we can patch sync_hour on the instance
        # OR rely on mocking http_client.
        # But sync_hour logic is inside SyncManager.
        # Let's mock sync_hour method for isolation of sync_all logic
        with patch.object(self.sync_manager, "sync_hour") as mock_sync_hour:
            mock_sync_hour.side_effect = [
                True,
                False,
            ]  # For h2, h3 (h1 is skipped before call)

            with patch("builtins.print"):
                result = self.sync_manager.sync_all()

        self.assertEqual(result["skipped"], 1)  # h1
        self.assertEqual(result["synced"], 1)  # h2
        self.assertEqual(result["failed"], 1)  # h3

    def test_sync_all_max_hours(self):
        """Test sync_all with max_hours limit."""
        files = {"h1": ["f1"], "h2": ["f2"], "h3": ["f3"]}
        self.sync_manager.data_aggregator.group_files_by_hour.return_value = files

        # Ensure items are not considered already synced
        self.sync_manager.sync_state.is_hour_synced.return_value = False

        # Mock sync_hour to always succeed
        with patch.object(self.sync_manager, "sync_hour", return_value=True):
            with patch("builtins.print"):
                result = self.sync_manager.sync_all(max_hours=2)

        # Should process last 2 hours (h2, h3)
        self.assertEqual(result["synced"], 2)

    def test_get_sync_status(self):
        """Test get_sync_status."""
        self.sync_manager.data_aggregator.group_files_by_hour.return_value = {
            "h1": [],
            "h2": [],
        }
        self.sync_manager.sync_state.get_sync_statistics.return_value = {
            "stats": "dummy"
        }
        self.sync_manager.device_identifier.get_device_name.return_value = "TestDevice"

        status = self.sync_manager.get_sync_status()

        self.assertEqual(status["stats"], "dummy")
        self.assertEqual(status["endpoint"], self.endpoint)
        self.assertEqual(status["device"], "TestDevice")


class TestSyncCLI(unittest.TestCase):
    """Test cases for SyncManager CLI."""

    @patch("activity_tracker.sync.SyncManager")
    def test_main_status(self, mock_manager_class):
        """Test main status command."""
        mock_manager = mock_manager_class.return_value
        mock_manager.get_sync_status.return_value = {
            "device": "Test",
            "total_hours": 10,
            "synced_hours": 5,
            "pending_hours": 5,
            "endpoint": "http://test",
            "last_sync": "never",
        }

        with patch.object(sys, "argv", ["sync_manager.py", "status"]):
            with patch("builtins.print") as mock_print:
                main()

        mock_manager.get_sync_status.assert_called()
        mock_print.assert_any_call("Sync Status:")

    @patch("activity_tracker.sync.SyncManager")
    def test_main_sync(self, mock_manager_class):
        """Test main sync command."""
        mock_manager = mock_manager_class.return_value
        mock_manager.sync_all.return_value = {"synced": 1, "failed": 0, "skipped": 0}

        with patch.object(sys, "argv", ["sync_manager.py", "sync"]):
            with patch("builtins.print") as mock_print:
                main()

        mock_manager.sync_all.assert_called_with()

    @patch("activity_tracker.sync.SyncManager")
    def test_main_force(self, mock_manager_class):
        """Test main force command."""
        mock_manager = mock_manager_class.return_value
        mock_manager.sync_all.return_value = {"synced": 1, "failed": 0, "skipped": 0}

        with patch.object(sys, "argv", ["sync_manager.py", "force"]):
            with patch("builtins.print"):
                main()

        mock_manager.sync_all.assert_called_with(force=True)

    @patch("activity_tracker.sync.SyncManager")
    def test_main_recent(self, mock_manager_class):
        """Test main recent command."""
        mock_manager = mock_manager_class.return_value
        mock_manager.sync_all.return_value = {"synced": 1, "failed": 0, "skipped": 0}

        with patch.object(sys, "argv", ["sync_manager.py", "recent"]):
            with patch("builtins.print"):
                main()

        mock_manager.sync_all.assert_called_with(max_hours=24)

    def test_main_help(self):
        """Test main help."""
        with patch.object(sys, "argv", ["sync_manager.py", "--help"]):
            with patch("builtins.print") as mock_print:
                main()

        args, _ = mock_print.call_args_list[0]
        self.assertEqual(args[0], "Sync Manager for Activity Tracker")

    def test_main_unknown_command(self):
        """Test main unknown command."""
        with patch.object(sys, "argv", ["sync_manager.py", "unknown"]):
            with patch("builtins.print") as mock_print:
                main()

        mock_print.assert_any_call("Unknown command: unknown")


if __name__ == "__main__":
    unittest.main()
