"""Tests for http_sync module functionality."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests


class TestDeviceIdentifier(unittest.TestCase):
    """Test cases for DeviceIdentifier class."""

    def setUp(self):
        """Set up test fixtures."""
        from activity_tracker.http_sync import DeviceIdentifier

        self.identifier = DeviceIdentifier()

    @patch("socket.gethostname")
    def test_get_device_name_returns_hostname(self, mock_gethostname):
        """Test getting device name from hostname."""
        mock_gethostname.return_value = "my-macbook"

        result = self.identifier.get_device_name()

        self.assertEqual(result, "my-macbook")

    @patch("socket.gethostname")
    def test_get_device_name_removes_local_suffix(self, mock_gethostname):
        """Test that .local suffix is removed from hostname."""
        mock_gethostname.return_value = "my-macbook.local"

        result = self.identifier.get_device_name()

        self.assertEqual(result, "my-macbook")

    @patch("socket.gethostname")
    @patch("platform.node")
    def test_get_device_name_fallback_to_platform(self, mock_node, mock_gethostname):
        """Test fallback to platform.node() for generic hostnames."""
        mock_gethostname.return_value = "localhost"
        mock_node.return_value = "real-hostname"

        result = self.identifier.get_device_name()

        self.assertEqual(result, "real-hostname")

    @patch("socket.gethostname")
    @patch("platform.machine")
    def test_get_device_name_exception_fallback(self, mock_machine, mock_gethostname):
        """Test fallback on exception."""
        mock_gethostname.side_effect = OSError("Network error")
        mock_machine.return_value = "arm64"

        result = self.identifier.get_device_name()

        self.assertEqual(result, "macos-arm64")


class TestSyncPayloadBuilder(unittest.TestCase):
    """Test cases for SyncPayloadBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        from activity_tracker.http_sync import SyncPayloadBuilder

        self.builder = SyncPayloadBuilder()

    def test_create_sync_payload(self):
        """Test creating sync payload."""
        hour_key = "2024-01-15_14"
        hour_data = {
            "applications": {"App1": 30.0},
            "total_time": 30.0,
            "files_processed": 1,
        }

        with patch.object(
            self.builder.device_identifier,
            "get_device_name",
            return_value="test-device",
        ):
            result = self.builder.create_sync_payload(hour_key, hour_data)

        self.assertEqual(result["hour"], "2024-01-15_14")
        self.assertEqual(result["data"], hour_data)
        self.assertEqual(result["source"], "macos-activity-tracker")
        self.assertEqual(result["device"], "test-device")
        self.assertEqual(result["version"], "1.0")

    def test_create_sync_payload_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        hour_key = "2024-01-15_14"
        hour_data = {"applications": {}, "total_time": 0, "files_processed": 0}

        with patch.object(
            self.builder.device_identifier, "get_device_name", return_value="test"
        ):
            result = self.builder.create_sync_payload(hour_key, hour_data)

        # Should be valid ISO format
        timestamp = result["timestamp"]
        dt = datetime.fromisoformat(timestamp)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.hour, 14)


class TestHttpSyncClient(unittest.TestCase):
    """Test cases for HttpSyncClient class."""

    def setUp(self):
        """Set up test fixtures."""
        from activity_tracker.http_sync import HttpSyncClient

        self.client = HttpSyncClient(endpoint="https://test.example.com/api")

    def test_initialization(self):
        """Test HttpSyncClient initialization."""
        self.assertEqual(self.client.endpoint, "https://test.example.com/api")

    @patch("requests.post")
    def test_sync_hour_data_success(self, mock_post):
        """Test successful sync request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        hour_data = {"total_time": 60.0, "files_processed": 1, "applications": {}}

        with patch("builtins.print"):
            result = self.client.sync_hour_data("2024-01-15_14", hour_data)

        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_sync_hour_data_failure(self, mock_post):
        """Test failed sync request."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        hour_data = {"total_time": 60.0, "files_processed": 1, "applications": {}}

        with patch("builtins.print"):
            result = self.client.sync_hour_data("2024-01-15_14", hour_data)

        self.assertFalse(result)

    @patch("requests.post")
    def test_sync_hour_data_network_error(self, mock_post):
        """Test network error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        hour_data = {"total_time": 60.0, "files_processed": 1, "applications": {}}

        with patch("builtins.print"):
            result = self.client.sync_hour_data("2024-01-15_14", hour_data)

        self.assertFalse(result)

    @patch("requests.post")
    def test_sync_hour_data_timeout(self, mock_post):
        """Test timeout error handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        hour_data = {"total_time": 60.0, "files_processed": 1, "applications": {}}

        with patch("builtins.print"):
            result = self.client.sync_hour_data("2024-01-15_14", hour_data)

        self.assertFalse(result)

    @patch("requests.get")
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.client.test_connection()

        self.assertTrue(result)

    @patch("requests.get")
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")

        result = self.client.test_connection()

        self.assertFalse(result)


class TestSyncResultCollector(unittest.TestCase):
    """Test cases for SyncResultCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        from activity_tracker.http_sync import SyncResultCollector

        self.collector = SyncResultCollector()

    def test_initialization(self):
        """Test SyncResultCollector initialization."""
        results = self.collector.get_results()
        self.assertEqual(results["synced"], 0)
        self.assertEqual(results["failed"], 0)
        self.assertEqual(results["skipped"], 0)

    def test_record_sync_success(self):
        """Test recording successful sync."""
        self.collector.record_sync_success()
        self.collector.record_sync_success()

        results = self.collector.get_results()
        self.assertEqual(results["synced"], 2)

    def test_record_sync_failure(self):
        """Test recording failed sync."""
        self.collector.record_sync_failure()

        results = self.collector.get_results()
        self.assertEqual(results["failed"], 1)

    def test_record_sync_skip(self):
        """Test recording skipped sync."""
        self.collector.record_sync_skip()
        self.collector.record_sync_skip()
        self.collector.record_sync_skip()

        results = self.collector.get_results()
        self.assertEqual(results["skipped"], 3)

    def test_get_results_returns_copy(self):
        """Test that get_results returns a copy."""
        self.collector.record_sync_success()
        results = self.collector.get_results()
        results["synced"] = 999

        # Original should be unchanged
        original_results = self.collector.get_results()
        self.assertEqual(original_results["synced"], 1)


if __name__ == "__main__":
    unittest.main()
