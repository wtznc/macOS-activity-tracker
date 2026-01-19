"""Tests for activity_monitor module functionality."""

import unittest
from unittest.mock import MagicMock, patch


class TestActivityMonitor(unittest.TestCase):
    """Test cases for ActivityMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.activity_monitor import ActivityMonitor

            self.monitor = ActivityMonitor(
                include_window_titles=True,
                idle_threshold=300,
                debounce_delay=1.0,
            )

    def test_initialization(self):
        """Test ActivityMonitor initialization."""
        self.assertTrue(self.monitor.include_window_titles)
        self.assertEqual(self.monitor.debounce_delay, 1.0)
        self.assertIsNone(self.monitor.last_stable_app)
        self.assertIsNone(self.monitor.app_change_time)

    def test_initialization_without_window_titles(self):
        """Test initialization without window titles."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.activity_monitor import ActivityMonitor

            monitor = ActivityMonitor(include_window_titles=False)

        self.assertFalse(monitor.include_window_titles)
        self.assertIsNone(monitor.window_detector)

    def test_should_record_activity_returns_true_when_not_idle(self):
        """Test activity recording check when not idle."""
        self.monitor.idle_detector.is_idle = False
        result = self.monitor.should_record_activity()
        self.assertTrue(result)

    def test_should_record_activity_returns_false_when_idle(self):
        """Test activity recording check when idle."""
        self.monitor.idle_detector.is_idle = True
        result = self.monitor.should_record_activity()
        self.assertFalse(result)

    def test_get_session_total_time(self):
        """Test getting total session time."""
        self.monitor.session_tracker.current_session = {
            "App1": 30.0,
            "App2": 25.0,
        }
        result = self.monitor.get_session_total_time()
        self.assertEqual(result, 55.0)

    def test_clear_session_data_returns_and_clears(self):
        """Test clearing session data."""
        self.monitor.session_tracker.current_session = {
            "App1": 30.0,
        }

        result = self.monitor.clear_session_data()

        self.assertEqual(result, {"App1": 30.0})
        self.assertEqual(self.monitor.session_tracker.current_session, {})


class TestActivityMonitorAppChange(unittest.TestCase):
    """Test cases for app change detection with debouncing."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.activity_monitor import ActivityMonitor

            self.monitor = ActivityMonitor(
                include_window_titles=False,
                debounce_delay=1.0,
            )

    @patch("time.time")
    def test_check_app_change_starts_debounce(self, mock_time):
        """Test that app change starts debounce timer."""
        mock_time.return_value = 100.0
        self.monitor.last_stable_app = "Safari"

        current_app, start_time = self.monitor.check_app_change(
            "Safari", "Chrome", 90.0
        )

        # Should not change yet (debouncing)
        self.assertEqual(current_app, "Safari")
        self.assertIsNotNone(self.monitor.app_change_time)

    @patch("time.time")
    def test_check_app_change_confirms_after_debounce(self, mock_time):
        """Test that app change confirms after debounce delay."""
        mock_time.return_value = 102.0  # 2 seconds after change
        self.monitor.last_stable_app = "Safari"
        self.monitor.app_change_time = 100.0  # Started 2 seconds ago

        current_app, start_time = self.monitor.check_app_change(
            "Safari", "Chrome", 90.0
        )

        # Should change now
        self.assertEqual(current_app, "Chrome")
        self.assertEqual(self.monitor.last_stable_app, "Chrome")

    @patch("time.time")
    def test_check_app_change_no_change_same_app(self, mock_time):
        """Test no change when app stays the same."""
        mock_time.return_value = 100.0
        self.monitor.last_stable_app = "Safari"

        current_app, start_time = self.monitor.check_app_change(
            "Safari", "Safari", 90.0
        )

        self.assertEqual(current_app, "Safari")
        self.assertIsNone(self.monitor.app_change_time)


class TestActivityLogger(unittest.TestCase):
    """Test cases for ActivityLogger class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.activity_monitor import ActivityLogger

            self.logger = ActivityLogger(verbose=True)

    def test_initialization(self):
        """Test ActivityLogger initialization."""
        self.assertTrue(self.logger.verbose)

    def test_initialization_quiet_mode(self):
        """Test ActivityLogger in quiet mode."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.activity_monitor import ActivityLogger

            logger = ActivityLogger(verbose=False)
        self.assertFalse(logger.verbose)

    @patch("builtins.print")
    def test_log_tracking_start_verbose(self, mock_print):
        """Test tracking start log in verbose mode."""
        self.logger.log_tracking_start(include_window_titles=True)
        self.assertTrue(mock_print.called)

    @patch("builtins.print")
    def test_log_tracking_start_quiet(self, mock_print):
        """Test tracking start log in quiet mode."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.activity_monitor import ActivityLogger

            logger = ActivityLogger(verbose=False)

        logger.log_tracking_start(include_window_titles=True)
        mock_print.assert_not_called()

    @patch("builtins.print")
    def test_log_data_save_verbose(self, mock_print):
        """Test data save log in verbose mode."""
        self.logger.log_data_save(55.5)
        self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
