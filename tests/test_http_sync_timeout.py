"""Tests for HTTP sync timeout configuration."""

import unittest
from unittest.mock import Mock, patch

import requests

from activity_tracker.http_sync import HttpSyncClient


class TestHttpSyncTimeout(unittest.TestCase):
    """Test cases for HTTP sync timeout configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HttpSyncClient(endpoint="http://test.example.com/api/data")

    @patch("requests.post")
    def test_sync_hour_data_uses_tuple_timeout(self, mock_post):
        """Test that sync_hour_data uses tuple timeout (connect, read)."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Sample hour data
        hour_key = "2024-01-15_14"
        hour_data = {
            "applications": {"App1": 30.0, "App2": 30.0},
            "total_time": 60.0,
            "files_processed": 2,
        }

        # Call sync_hour_data
        result = self.client.sync_hour_data(hour_key, hour_data)

        # Verify success
        self.assertTrue(result)

        # Verify that requests.post was called with tuple timeout
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertIn("timeout", call_kwargs)
        self.assertEqual(call_kwargs["timeout"], (5, 15))

    @patch("requests.get")
    def test_test_connection_uses_tuple_timeout(self, mock_get):
        """Test that test_connection uses tuple timeout (connect, read)."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call test_connection
        result = self.client.test_connection()

        # Verify success
        self.assertTrue(result)

        # Verify that requests.get was called with tuple timeout
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        self.assertIn("timeout", call_kwargs)
        self.assertEqual(call_kwargs["timeout"], (3, 10))

    @patch("requests.post")
    def test_sync_handles_connect_timeout(self, mock_post):
        """Test that sync properly handles connection timeout."""
        # Mock connection timeout
        mock_post.side_effect = requests.exceptions.ConnectTimeout(
            "Connection timeout"
        )

        hour_key = "2024-01-15_14"
        hour_data = {
            "applications": {"App1": 30.0},
            "total_time": 30.0,
            "files_processed": 1,
        }

        # Call sync_hour_data
        result = self.client.sync_hour_data(hour_key, hour_data)

        # Verify failure is handled
        self.assertFalse(result)

    @patch("requests.post")
    def test_sync_handles_read_timeout(self, mock_post):
        """Test that sync properly handles read timeout."""
        # Mock read timeout
        mock_post.side_effect = requests.exceptions.ReadTimeout("Read timeout")

        hour_key = "2024-01-15_14"
        hour_data = {
            "applications": {"App1": 30.0},
            "total_time": 30.0,
            "files_processed": 1,
        }

        # Call sync_hour_data
        result = self.client.sync_hour_data(hour_key, hour_data)

        # Verify failure is handled
        self.assertFalse(result)

    @patch("requests.get")
    def test_connection_test_handles_timeout(self, mock_get):
        """Test that test_connection handles timeout gracefully."""
        # Mock timeout
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        # Call test_connection
        result = self.client.test_connection()

        # Verify failure is handled
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
