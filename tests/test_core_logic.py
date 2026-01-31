"""Tests for internal logic of Pulse."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from pulse.core import TARGET_MINUTE_SECONDS, Pulse


class TestPulseLogic(unittest.TestCase):
    """Test cases for internal logic methods of Pulse."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = Pulse(
            data_dir="/tmp",
            interval=60,
            verbose=False,
        )
        # Mock external dependencies to avoid side effects
        self.tracker.monitor = MagicMock()
        self.tracker.logger = MagicMock()
        self.tracker.data_store = MagicMock()

    def test_is_minute_boundary_true(self):
        """Test detection of minute boundary crossing."""
        # Set last check time to a different minute
        self.tracker.last_check_time = datetime(2023, 1, 1, 12, 0, 0)

        # Patch datetime to return a time in the next minute
        with patch("pulse.core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 1, 0)
            result = self.tracker._is_minute_boundary()

        self.assertTrue(result)
        self.assertEqual(self.tracker.last_check_time.minute, 1)

    def test_is_minute_boundary_false(self):
        """Test when minute boundary is not crossed."""
        self.tracker.last_check_time = datetime(2023, 1, 1, 12, 0, 0)

        with patch("pulse.core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 30)
            result = self.tracker._is_minute_boundary()

        self.assertFalse(result)
        self.assertEqual(self.tracker.last_check_time.minute, 0)

    def test_calculate_time_in_current_minute_before_boundary(self):
        """Test time calculation when start_time is before last boundary."""
        # Last boundary at 1000
        last_boundary = datetime.fromtimestamp(1000)
        # Start time at 900 (before boundary)
        start_time = 900.0

        # Current time at 1030
        with patch("pulse.core.time.time", return_value=1030.0):
            result = self.tracker._calculate_time_in_current_minute(
                start_time, last_boundary
            )

        # Should be 1030 - 1000 = 30
        self.assertEqual(result, 30.0)

    def test_calculate_time_in_current_minute_after_boundary(self):
        """Test time calculation when start_time is after last boundary."""
        # Last boundary at 1000
        last_boundary = datetime.fromtimestamp(1000)
        # Start time at 1010 (after boundary)
        start_time = 1010.0

        # Current time at 1030
        with patch("pulse.core.time.time", return_value=1030.0):
            result = self.tracker._calculate_time_in_current_minute(
                start_time, last_boundary
            )

        # Should be 1030 - 1010 = 20
        self.assertEqual(result, 20.0)

    def test_get_current_app_time(self):
        """Test getting current app time bounded."""
        self.tracker.last_check_time = datetime.fromtimestamp(1000)

        # Case 1: No current app
        self.assertEqual(self.tracker._get_current_app_time(None, 1000), 0.0)

        # Case 2: Normal duration (30s)
        with patch("pulse.core.time.time", return_value=1030.0):
            result = self.tracker._get_current_app_time("App", 1000.0)
            self.assertEqual(result, 30.0)

        # Case 3: Overflow (>60s) - should cap at 60
        with patch("pulse.core.time.time", return_value=1070.0):
            result = self.tracker._get_current_app_time("App", 1000.0)
            self.assertEqual(result, 60.0)

    def test_normalize_to_minute(self):
        """Test normalization of durations to exactly 60 seconds."""
        # Case 1: Already exactly 60 seconds
        data = {"App1": 30.0, "App2": 30.0}  # Total 60
        result = self.tracker._normalize_to_minute(data)
        self.assertEqual(sum(result.values()), 60.0)
        self.assertEqual(result["App1"], 30.0)
        self.assertEqual(result["App2"], 30.0)

        # Case 2: Over 60 seconds - should scale down
        data = {"App1": 60.0, "App2": 60.0}  # Total 120
        result = self.tracker._normalize_to_minute(data)
        self.assertEqual(sum(result.values()), 60.0)
        self.assertEqual(result["App1"], 30.0)
        self.assertEqual(result["App2"], 30.0)

        # Case 3: Under 60 seconds - should scale up
        data = {"App1": 15.0, "App2": 15.0}  # Total 30
        result = self.tracker._normalize_to_minute(data)
        self.assertEqual(sum(result.values()), 60.0)
        self.assertEqual(result["App1"], 30.0)
        self.assertEqual(result["App2"], 30.0)

        # Case 4: Single app - should be exactly 60
        data = {"App1": 45.0}
        result = self.tracker._normalize_to_minute(data)
        self.assertEqual(result["App1"], 60.0)

        # Case 5: Empty data
        self.assertEqual(self.tracker._normalize_to_minute({}), {})

        # Case 6: Precision - values should have max 2 decimal places
        data = {"App1": 33.333, "App2": 66.666}  # Total ~100
        result = self.tracker._normalize_to_minute(data)
        self.assertEqual(sum(result.values()), 60.0)
        for value in result.values():
            self.assertEqual(value, round(value, 2))

    def test_build_bounded_data(self):
        """Test building bounded data dictionary."""
        self.tracker.last_check_time = datetime.fromtimestamp(1000)

        # Setup session data
        session_data = {"BackgroundApp": 10.0}
        current_app = "ActiveApp"
        time_since_boundary = 20.0

        # Mock time.time to define max_reasonable_time window
        # current_time = 1030, last_boundary = 1000 -> max 30s window
        with patch("pulse.core.time.time", return_value=1030.0):
            result = self.tracker._build_bounded_data(
                session_data, current_app, time_since_boundary
            )

        self.assertEqual(result["BackgroundApp"], 10.0)
        self.assertEqual(result["ActiveApp"], 20.0)

    def test_build_bounded_data_caps_background(self):
        """Test that background apps are capped by elapsed time."""
        self.tracker.last_check_time = datetime.fromtimestamp(1000)

        # Background app claims 50s, but only 30s have passed
        session_data = {"BackgroundApp": 50.0}
        current_app = None
        time_since_boundary = 0.0

        with patch("pulse.core.time.time", return_value=1030.0):
            result = self.tracker._build_bounded_data(
                session_data, current_app, time_since_boundary
            )

        # Should be capped at 30s (max_reasonable_time)
        self.assertEqual(result["BackgroundApp"], 30.0)

    def test_check_save_interval_no_boundary(self):
        """Test check_save_interval when no boundary crossed."""
        # Mock _is_minute_boundary to return False
        self.tracker._is_minute_boundary = MagicMock(return_value=False)

        start_time = 1000.0
        new_start_time = self.tracker._check_save_interval("App", start_time)

        self.assertEqual(new_start_time, start_time)
        self.tracker.monitor.clear_session_data.assert_not_called()

    def test_check_save_interval_boundary(self):
        """Test check_save_interval when boundary crossed."""
        self.tracker._is_minute_boundary = MagicMock(return_value=True)
        self.tracker._get_bounded_session_data = MagicMock(return_value={"App": 10})
        self.tracker._save_and_log = MagicMock()

        start_time = 1000.0
        with patch("pulse.core.time.time", return_value=1060.0):
            new_start_time = self.tracker._check_save_interval("App", start_time)

        self.assertEqual(new_start_time, 1060.0)
        self.tracker._save_and_log.assert_called_once()

    def test_save_final_data(self):
        """Test saving final data on exit."""
        current_app = "App"
        start_time = 1000.0

        self.tracker.monitor.clear_session_data.return_value = {"Other": 5}

        with patch("pulse.core.time.time", return_value=1010.0):
            self.tracker._save_final_data(current_app, start_time)

        # Should add activity for current app (10s)
        self.tracker.monitor.session_tracker.add_activity.assert_called_with(
            "App", 10.0
        )
        # Should save merged data
        self.tracker.data_store.merge_and_save_session_data.assert_called_with(
            {"Other": 5}
        )

    def test_track_activity_loop(self):
        """Test the main tracking loop (one iteration)."""
        # Setup mocks
        self.tracker.running = True
        self.tracker.monitor.include_window_titles = True

        # Mock monitor methods
        self.tracker.monitor.idle_detector.check_idle_state.return_value = False
        self.tracker.monitor.handle_idle_transition.return_value = 1000.0
        self.tracker.monitor.get_current_activity.return_value = "App"
        self.tracker.monitor.check_app_change.return_value = ("App", 1000.0)

        # Mock internal check
        self.tracker._check_save_interval = MagicMock(return_value=1000.0)

        # Mock time.sleep to stop the loop by side effect or just run once
        # Strategy: Run once, then set running=False
        def stop_loop(*args):
            self.tracker.running = False

        with patch("pulse.core.time.sleep", side_effect=stop_loop) as mock_sleep:
            with patch("pulse.core.time.time", return_value=1000.0):
                self.tracker.track_activity()

        # Verify call chain
        self.tracker.logger.log_tracking_start.assert_called()
        self.tracker.monitor.get_current_activity.assert_called()
        self.tracker.monitor.check_app_change.assert_called()
        self.tracker._check_save_interval.assert_called()
        self.tracker.logger.log_tracking_stop.assert_called()

    def test_track_activity_idle(self):
        """Test tracking loop when idle."""
        self.tracker.running = True

        # Mock idle
        self.tracker.monitor.idle_detector.check_idle_state.return_value = True
        self.tracker.monitor.idle_detector.is_idle = True

        # Stop loop after first sleep
        def stop_loop(*args):
            self.tracker.running = False

        with patch("pulse.core.time.sleep", side_effect=stop_loop) as mock_sleep:
            self.tracker.track_activity()

        # Should check idle and sleep, but NOT get activity
        self.tracker.monitor.idle_detector.check_idle_state.assert_called()
        self.tracker.monitor.get_current_activity.assert_not_called()

    def test_track_activity_exception(self):
        """Test exception handling in tracking loop."""
        self.tracker.running = True

        # Raise exception in loop
        self.tracker.monitor.idle_detector.check_idle_state.side_effect = Exception(
            "Test Error"
        )

        # Stop loop after exception handling
        # It will print error and sleep(5). We want to break loop after that.
        # side_effect on sleep: first call (from exception handler) -> stop loop
        def stop_loop(*args):
            self.tracker.running = False

        with patch("pulse.core.time.sleep", side_effect=stop_loop) as mock_sleep:
            with patch("builtins.print") as mock_print:
                self.tracker.track_activity()

        mock_print.assert_called_with("Error in tracking loop: Test Error")
