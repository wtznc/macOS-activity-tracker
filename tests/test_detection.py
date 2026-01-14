"""Tests for detection module functionality."""

import time
import unittest
from unittest.mock import Mock, patch

from activity_tracker.detection import WindowTitleDetector


class TestWindowTitleDetector(unittest.TestCase):
    """Test cases for WindowTitleDetector with caching and metrics."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = WindowTitleDetector(cache_ttl=2.0, applescript_timeout=0.5)

    def test_initialization(self):
        """Test WindowTitleDetector initialization."""
        self.assertEqual(self.detector.cache_ttl, 2.0)
        self.assertEqual(self.detector.applescript_timeout, 0.5)
        self.assertEqual(self.detector._title_cache, {})
        self.assertEqual(self.detector._metrics["total_calls"], 0)
        self.assertEqual(self.detector._metrics["cache_hits"], 0)

    def test_cache_functionality(self):
        """Test window title caching."""
        app_name = "Safari"
        title = "GitHub - Activity Tracker"

        # Update cache
        self.detector._update_cache(app_name, title)

        # Retrieve from cache
        cached_title = self.detector._get_from_cache(app_name)
        self.assertEqual(cached_title, title)

    def test_cache_expiration(self):
        """Test cache expiration after TTL."""
        app_name = "Safari"
        title = "GitHub"

        # Update cache with short TTL
        detector = WindowTitleDetector(cache_ttl=0.1, applescript_timeout=0.5)
        detector._update_cache(app_name, title)

        # Should retrieve from cache immediately
        self.assertEqual(detector._get_from_cache(app_name), title)

        # Wait for expiration
        time.sleep(0.15)

        # Should return None after expiration
        self.assertIsNone(detector._get_from_cache(app_name))

    @patch("activity_tracker.detection.subprocess.run")
    def test_applescript_timeout_setting(self, mock_run):
        """Test that AppleScript uses the configured timeout."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test Window\n"
        mock_run.return_value = mock_result

        title = self.detector._get_title_via_applescript("Safari")

        # Verify timeout parameter
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        self.assertEqual(call_kwargs["timeout"], 0.5)
        self.assertEqual(title, "Test Window")

    @patch("activity_tracker.detection.subprocess.run")
    def test_metrics_tracking(self, mock_run):
        """Test performance metrics are tracked correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test Window\n"
        mock_run.return_value = mock_result

        # Make some calls
        self.detector._get_title_via_applescript("Safari")
        self.detector._get_title_via_applescript("Google Chrome")

        metrics = self.detector.get_metrics()
        self.assertEqual(metrics["applescript_calls"], 2)
        self.assertGreater(metrics["applescript_total_time"], 0)
        self.assertGreater(metrics["avg_applescript_time"], 0)

    @patch("activity_tracker.detection.subprocess.run")
    def test_timeout_metrics(self, mock_run):
        """Test timeout metrics are recorded."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 0.5)

        # Call should handle timeout gracefully
        title = self.detector._get_title_via_applescript("Safari")
        self.assertIsNone(title)

        metrics = self.detector.get_metrics()
        self.assertEqual(metrics["applescript_timeouts"], 1)

    @patch("activity_tracker.detection.subprocess.run")
    @patch("activity_tracker.detection.CGWindowListCopyWindowInfo")
    def test_fallback_to_quartz_on_timeout(self, mock_quartz, mock_run):
        """Test that Quartz is used as fallback when AppleScript times out."""
        import subprocess

        # Make AppleScript timeout
        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 0.5)

        # Mock Quartz response
        mock_quartz.return_value = [
            {
                "kCGWindowOwnerName": "Safari",
                "kCGWindowName": "Fallback Title",
            }
        ]

        # Should fallback to Quartz
        title = self.detector.get_window_title("Safari")
        self.assertEqual(title, "Fallback Title")

        # Verify metrics
        metrics = self.detector.get_metrics()
        self.assertEqual(metrics["applescript_timeouts"], 1)
        self.assertEqual(metrics["quartz_fallbacks"], 1)

    @patch("activity_tracker.detection.subprocess.run")
    def test_cache_hit_metrics(self, mock_run):
        """Test that cache hits are tracked in metrics."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Cached Title\n"
        mock_run.return_value = mock_result

        # First call - cache miss
        title1 = self.detector.get_window_title("Safari")
        self.assertEqual(title1, "Cached Title")

        # Second call - should hit cache
        title2 = self.detector.get_window_title("Safari")
        self.assertEqual(title2, "Cached Title")

        metrics = self.detector.get_metrics()
        self.assertEqual(metrics["total_calls"], 2)
        self.assertEqual(metrics["cache_hits"], 1)
        # Only one AppleScript call should have been made
        self.assertEqual(metrics["applescript_calls"], 1)

    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        # Set some metrics
        self.detector._metrics["total_calls"] = 10
        self.detector._metrics["cache_hits"] = 5

        # Reset metrics
        self.detector.reset_metrics()

        # Verify reset
        metrics = self.detector.get_metrics()
        self.assertEqual(metrics["total_calls"], 0)
        self.assertEqual(metrics["cache_hits"], 0)
        self.assertEqual(metrics["applescript_total_time"], 0.0)

    @patch("activity_tracker.detection.subprocess.run")
    @patch("activity_tracker.detection.CGWindowListCopyWindowInfo")
    def test_vscode_special_handling(self, mock_quartz, mock_run):
        """Test special handling for VS Code."""
        import subprocess

        # Make AppleScript fail
        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 0.5)

        # Mock Quartz with no direct match
        mock_quartz.return_value = [
            {
                "kCGWindowOwnerName": "Code",
                "kCGWindowName": "",
                "kCGWindowLayer": 0,
                "kCGWindowBounds": {"Width": 800, "Height": 600},
            }
        ]

        # Should use fallback title for VS Code
        title = self.detector.get_window_title("Visual Studio Code")
        self.assertEqual(title, "Editor Window")

    def test_custom_timeout_configuration(self):
        """Test that custom timeout can be configured."""
        custom_detector = WindowTitleDetector(cache_ttl=5.0, applescript_timeout=1.0)
        self.assertEqual(custom_detector.applescript_timeout, 1.0)
        self.assertEqual(custom_detector.cache_ttl, 5.0)

    @patch("activity_tracker.detection.subprocess.run")
    def test_reduced_timeout_from_default(self, mock_run):
        """Test that default timeout is reduced from 2s to 0.5s."""
        # Default timeout should be 0.5s
        default_detector = WindowTitleDetector()
        self.assertEqual(default_detector.applescript_timeout, 0.5)

        # Compare to old timeout of 2s
        self.assertLess(default_detector.applescript_timeout, 2.0)


if __name__ == "__main__":
    unittest.main()
