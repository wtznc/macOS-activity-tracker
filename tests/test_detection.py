"""Tests for detection module functionality."""

import subprocess
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest


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

            self.detector = WindowTitleDetector()

    def test_app_mapping_contains_common_apps(self):
        """Test that APP_MAPPING contains common applications."""
        expected_apps = ["Safari", "Google Chrome", "Firefox", "Terminal"]
        for app in expected_apps:
            self.assertIn(app, self.detector.APP_MAPPING)

    @patch("subprocess.run")
    def test_get_title_via_applescript_returns_title(self, mock_run):
        """Test AppleScript window title detection."""
        mock_run.return_value = Mock(returncode=0, stdout="Test Window Title\n")

        result = self.detector._get_title_via_applescript("Safari")

        self.assertEqual(result, "Test Window Title")

    @patch("subprocess.run")
    def test_get_title_via_applescript_handles_timeout(self, mock_run):
        """Test AppleScript timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 1.0)

        result = self.detector._get_title_via_applescript("Safari")

        self.assertIsNone(result)

    @patch("subprocess.run")
    def test_get_title_via_applescript_handles_empty_output(self, mock_run):
        """Test AppleScript empty output handling."""
        mock_run.return_value = Mock(returncode=0, stdout="")

        result = self.detector._get_title_via_applescript("Safari")

        self.assertIsNone(result)


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
