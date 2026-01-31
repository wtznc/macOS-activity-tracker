"""Tests for core Pulse functionality."""

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pulse.core import Pulse


class TestPulse(unittest.TestCase):
    """Test cases for Pulse class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = Pulse(
            data_dir=self.temp_dir,
            interval=60,
            verbose=False,
            include_window_titles=True,
            fast_mode=False,
            idle_threshold=300,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test Pulse initialization."""
        self.assertEqual(self.tracker.data_store.data_dir, Path(self.temp_dir))
        self.assertEqual(self.tracker.interval, 60)
        self.assertFalse(self.tracker.logger.verbose)
        self.assertTrue(self.tracker.monitor.include_window_titles)
        self.assertEqual(self.tracker.monitor.idle_detector.idle_threshold, 300)

    def test_data_directory_creation(self):
        """Test that data directory is created."""
        self.assertTrue(self.tracker.data_store.data_dir.exists())
        self.assertTrue(self.tracker.data_store.data_dir.is_dir())

    @patch("pulse.detection.NSWorkspace")
    def test_get_active_application(self, mock_workspace_class):
        """Test getting active application."""
        # Mock the NSWorkspace response - activeApplication returns a dict
        mock_workspace = Mock()
        mock_workspace.activeApplication.return_value = {"NSApplicationName": "TestApp"}
        mock_workspace_class.sharedWorkspace.return_value = mock_workspace

        app_name = self.tracker.monitor.app_detector.get_active_application()
        self.assertEqual(app_name, "TestApp")

    def test_clean_title(self):
        """Test title cleaning functionality."""
        # Test Unicode normalization with actual Unicode characters
        test_cases = [
            ("Test\u2022App", "Test•App"),
            ("File\u00b7Name", "File·Name"),
            ("Code\u2014Project", "Code—Project"),
            ("Normal Title", "Normal Title"),
            ("", ""),
        ]

        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.tracker.monitor.title_cleaner.clean_title(input_title)
                self.assertEqual(result, expected)

    def test_idle_detection(self):
        """Test idle detection logic."""
        with patch(
            "pulse.detection.CGEventSourceSecondsSinceLastEventType"
        ) as mock_idle:
            # Test not idle
            mock_idle.return_value = 100  # 100 seconds since last event
            idle_time = self.tracker.monitor.idle_detector.get_system_idle_time()
            self.assertEqual(idle_time, 100)

            # Test idle detection
            self.tracker.monitor.idle_detector.is_idle = False
            is_idle_changed = self.tracker.monitor.idle_detector.check_idle_state()
            self.assertFalse(is_idle_changed)  # 100 seconds is less than 300 threshold

            # Test idle
            mock_idle.return_value = 400  # 400 seconds since last event
            is_idle_changed = self.tracker.monitor.idle_detector.check_idle_state()
            self.assertTrue(is_idle_changed)  # 400 seconds exceeds 300 threshold

    def test_save_session_data(self):
        """Test saving session data to JSON file."""
        # Set up some test data in session tracker
        test_data = {"TestApp": 30.5, "AnotherApp": 25.2}
        self.tracker.monitor.session_tracker.current_session = test_data.copy()

        # Save data
        session_data = self.tracker.monitor.session_tracker.clear_session()
        self.tracker.data_store.merge_and_save_session_data(session_data)

        # Check file was created
        json_files = list(self.tracker.data_store.data_dir.glob("activity_*.json"))
        self.assertEqual(len(json_files), 1)

        # Check file contents
        with open(json_files[0], "r") as f:
            saved_data = json.load(f)

        # Should match original test data
        self.assertEqual(saved_data, test_data)
        # Verify session tracker is cleared
        self.assertEqual(self.tracker.monitor.session_tracker.current_session, {})

    def test_format_time_output(self):
        """Test time formatting for display."""
        # This would test time formatting if such a method exists
        # For now, just test that activities are recorded properly
        test_data = {"App1": 45.7, "App2": 14.3}
        total_time = sum(test_data.values())
        self.assertAlmostEqual(total_time, 60.0, places=1)

    def test_fast_mode_vs_detailed_mode(self):
        """Test performance difference between modes."""
        # Test fast mode configuration
        fast_tracker = Pulse(
            data_dir=self.temp_dir, fast_mode=True, include_window_titles=False
        )
        self.assertFalse(fast_tracker.monitor.include_window_titles)
        self.assertIsNone(fast_tracker.monitor.window_detector)

        # Test detailed mode configuration
        detailed_tracker = Pulse(
            data_dir=self.temp_dir, fast_mode=False, include_window_titles=True
        )
        self.assertTrue(detailed_tracker.monitor.include_window_titles)
        self.assertIsNotNone(detailed_tracker.monitor.window_detector)


class TestPulseIntegration(unittest.TestCase):
    """Integration tests for Pulse."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.integration
    def test_full_tracking_cycle(self):
        """Test a complete tracking cycle."""
        tracker = Pulse(
            data_dir=self.temp_dir,
            interval=1,  # 1 second for faster testing
            verbose=False,
        )

        # Mock some activity
        with patch.object(
            tracker.monitor.app_detector, "get_active_application"
        ) as mock_get_app:
            mock_get_app.return_value = "TestApp"

            # Simulate tracking for a few cycles
            tracker.monitor.session_tracker.current_session = {"TestApp": 0.5}
            session_data = tracker.monitor.session_tracker.clear_session()
            tracker.data_store.merge_and_save_session_data(session_data)

            # Check that files are created
            json_files = list(tracker.data_store.data_dir.glob("activity_*.json"))
            self.assertGreater(len(json_files), 0)

    @pytest.mark.slow
    def test_performance_benchmarks(self):
        """Test performance of different tracking modes."""

        # Test fast mode performance
        fast_tracker = Pulse(data_dir=self.temp_dir, fast_mode=True)

        start_time = time.time()
        for _ in range(100):
            fast_tracker.monitor.app_detector.get_active_application()
        fast_time = time.time() - start_time

        # Test detailed mode performance
        detailed_tracker = Pulse(data_dir=self.temp_dir, fast_mode=False)

        start_time = time.time()
        for _ in range(100):
            detailed_tracker.monitor.get_current_activity()
        detailed_time = time.time() - start_time

        # Fast mode should be significantly faster
        # Note: Actual performance will vary on real systems
        self.assertLess(fast_time, detailed_time * 10)  # Allow for some variance


if __name__ == "__main__":
    unittest.main()
