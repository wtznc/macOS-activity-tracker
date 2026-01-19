"""Tests for detection module functionality."""

import subprocess
import time
import unittest
from unittest.mock import MagicMock, Mock, patch


class TestApplicationDetector(unittest.TestCase):
    """Test cases for ApplicationDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        # Import is done inside method to avoid macOS-specific import errors
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import ApplicationDetector

            self.detector = ApplicationDetector()

    @patch("activity_tracker.detection.NSWorkspace")
    def test_get_active_application_returns_name(self, mock_workspace_class):
        """Test that get_active_application returns app name."""
        mock_workspace = Mock()
        mock_workspace.activeApplication.return_value = {"NSApplicationName": "Safari"}
        mock_workspace_class.sharedWorkspace.return_value = mock_workspace

        result = self.detector.get_active_application()

        self.assertEqual(result, "Safari")

    @patch("activity_tracker.detection.NSWorkspace")
    def test_get_active_application_returns_none_when_no_app(
        self, mock_workspace_class
    ):
        """Test that get_active_application returns None when no active app."""
        mock_workspace = Mock()
        mock_workspace.activeApplication.return_value = None
        mock_workspace_class.sharedWorkspace.return_value = mock_workspace

        result = self.detector.get_active_application()

        self.assertIsNone(result)

    @patch("activity_tracker.detection.NSWorkspace")
    def test_get_active_application_handles_exception(self, mock_workspace_class):
        """Test that get_active_application handles exceptions gracefully."""
        mock_workspace_class.sharedWorkspace.side_effect = RuntimeError("Test error")

        result = self.detector.get_active_application()

        self.assertIsNone(result)


class TestWindowTitleDetector(unittest.TestCase):
    """Test cases for WindowTitleDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import WindowTitleDetector

            self.detector = WindowTitleDetector(cache_ttl=2.0, applescript_timeout=0.5)

    def test_initialization(self):
        """Test WindowTitleDetector initialization."""
        self.assertEqual(self.detector.cache_ttl, 2.0)
        self.assertEqual(self.detector.applescript_timeout, 0.5)
        self.assertEqual(self.detector._title_cache, {})
        self.assertEqual(self.detector._metrics["total_calls"], 0)
        self.assertEqual(self.detector._metrics["cache_hits"], 0)

    def test_app_mapping_contains_common_apps(self):
        """Test that APP_MAPPING contains common applications."""
        expected_apps = ["Safari", "Google Chrome", "Firefox", "Terminal"]
        for app in expected_apps:
            self.assertIn(app, self.detector.APP_MAPPING)

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
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import WindowTitleDetector

            app_name = "Safari"
            title = "GitHub"

            # Update cache with short TTL
            detector = WindowTitleDetector(cache_ttl=0.1, applescript_timeout=0.5)
            detector._update_cache(app_name, title)

            # Should retrieve from cache immediately
            self.assertEqual(detector._get_from_cache(app_name), title)

            # Wait for expiration (with buffer for slower systems)
            time.sleep(0.15)

            # Should return None after expiration
            self.assertIsNone(detector._get_from_cache(app_name))

    @patch("activity_tracker.detection.subprocess.run")
    def test_get_title_via_applescript_returns_title(self, mock_run):
        """Test AppleScript window title detection."""
        mock_run.return_value = Mock(returncode=0, stdout="Test Window Title\n")

        result = self.detector._get_title_via_applescript("Safari")

        self.assertEqual(result, "Test Window Title")

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
    def test_get_title_via_applescript_handles_timeout(self, mock_run):
        """Test AppleScript timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 0.5)

        result = self.detector._get_title_via_applescript("Safari")

        self.assertIsNone(result)

    @patch("activity_tracker.detection.subprocess.run")
    def test_get_title_via_applescript_handles_empty_output(self, mock_run):
        """Test AppleScript empty output handling."""
        mock_run.return_value = Mock(returncode=0, stdout="")

        result = self.detector._get_title_via_applescript("Safari")

        self.assertIsNone(result)

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
        """Test special handling for VS Code with empty window title."""
        # Make AppleScript fail
        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 0.5)

        # Mock Quartz with no direct match (empty kCGWindowName)
        mock_quartz.return_value = [
            {
                "kCGWindowOwnerName": "Code",
                "kCGWindowName": "",  # Empty title triggers fallback
                "kCGWindowLayer": 0,
                "kCGWindowBounds": {"Width": 800, "Height": 600},
            }
        ]

        # Should use fallback title for VS Code
        title = self.detector.get_window_title("Visual Studio Code")
        self.assertEqual(title, "Editor Window")

    def test_custom_timeout_configuration(self):
        """Test that custom timeout can be configured."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import WindowTitleDetector

            custom_detector = WindowTitleDetector(
                cache_ttl=5.0, applescript_timeout=1.0
            )
            self.assertEqual(custom_detector.applescript_timeout, 1.0)
            self.assertEqual(custom_detector.cache_ttl, 5.0)

    def test_reduced_timeout_from_default(self):
        """Test that default timeout is reduced from 2s to 0.5s."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import WindowTitleDetector

            # Default timeout should be 0.5s
            default_detector = WindowTitleDetector()
            self.assertEqual(default_detector.applescript_timeout, 0.5)

            # Compare to old timeout of 2s
            self.assertLess(default_detector.applescript_timeout, 2.0)


class TestIdleDetector(unittest.TestCase):
    """Test cases for IdleDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import IdleDetector

            self.detector = IdleDetector(idle_threshold=300)

    def test_initialization(self):
        """Test IdleDetector initialization."""
        self.assertEqual(self.detector.idle_threshold, 300)
        self.assertFalse(self.detector.is_idle)
        self.assertIsNone(self.detector.idle_start_time)

    @patch("activity_tracker.detection.CGEventSourceSecondsSinceLastEventType")
    def test_get_system_idle_time(self, mock_cg_event):
        """Test getting system idle time."""
        mock_cg_event.return_value = 150.5

        result = self.detector.get_system_idle_time()

        self.assertEqual(result, 150.5)

    @patch("activity_tracker.detection.CGEventSourceSecondsSinceLastEventType")
    def test_check_idle_state_becomes_idle(self, mock_cg_event):
        """Test idle state transition to idle."""
        mock_cg_event.return_value = 400  # Above 300 threshold

        self.detector.is_idle = False
        changed = self.detector.check_idle_state()

        self.assertTrue(changed)
        self.assertTrue(self.detector.is_idle)

    @patch("activity_tracker.detection.CGEventSourceSecondsSinceLastEventType")
    def test_check_idle_state_becomes_active(self, mock_cg_event):
        """Test idle state transition to active."""
        mock_cg_event.return_value = 5  # Below 300 threshold

        self.detector.is_idle = True
        changed = self.detector.check_idle_state()

        self.assertTrue(changed)
        self.assertFalse(self.detector.is_idle)

    @patch("activity_tracker.detection.CGEventSourceSecondsSinceLastEventType")
    def test_check_idle_state_no_change_when_still_active(self, mock_cg_event):
        """Test no change when remaining active."""
        mock_cg_event.return_value = 100  # Below threshold

        self.detector.is_idle = False
        changed = self.detector.check_idle_state()

        self.assertFalse(changed)
        self.assertFalse(self.detector.is_idle)


class TestTitleCleaner(unittest.TestCase):
    """Test cases for TitleCleaner class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.detection import TitleCleaner

            self.cleaner = TitleCleaner()

    def test_clean_title_handles_empty_string(self):
        """Test cleaning empty string."""
        result = self.cleaner.clean_title("")
        self.assertEqual(result, "")

    def test_clean_title_handles_none(self):
        """Test cleaning None value."""
        result = self.cleaner.clean_title(None)
        self.assertIsNone(result)

    def test_clean_title_replaces_unicode_characters(self):
        """Test Unicode character replacement."""
        # Test middle dot replacement
        result = self.cleaner.clean_title("Test\u00b7Title")
        self.assertEqual(result, "Test·Title")

    def test_clean_title_removes_vscode_suffix(self):
        """Test VS Code suffix removal."""
        result = self.cleaner.clean_title("main.py — Visual Studio Code")
        self.assertEqual(result, "main.py")

    def test_normalize_app_name_handles_osascript(self):
        """Test normalization of app names with osascript."""
        result = self.cleaner.normalize_app_name("Safari - osascript")
        self.assertEqual(result, "Safari")

    def test_normalize_app_name_preserves_normal_names(self):
        """Test preservation of normal app names."""
        result = self.cleaner.normalize_app_name("Safari - GitHub")
        self.assertEqual(result, "Safari - GitHub")


if __name__ == "__main__":
    unittest.main()
