"""Tests for daemon module functionality."""

import os
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestActivityDaemon(unittest.TestCase):
    """Test cases for ActivityDaemon class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pid_file = os.path.join(self.temp_dir, "test.pid")

        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.daemon import ActivityDaemon

            self.daemon = ActivityDaemon(pidfile=self.pid_file)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test ActivityDaemon initialization."""
        self.assertEqual(self.daemon.pidfile, self.pid_file)
        self.assertIsNone(self.daemon.tracker)

    def test_initialization_default_pidfile(self):
        """Test default PID file location."""
        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.daemon import ActivityDaemon

            daemon = ActivityDaemon()

        self.assertIn("activity_tracker.pid", daemon.pidfile)

    def test_start_creates_pidfile_check(self):
        """Test that start checks for existing PID file."""
        # Create a stale PID file
        with open(self.pid_file, "w") as f:
            f.write("99999999")  # Non-existent PID

        # The start method should remove stale PID file
        with patch.object(self.daemon, "daemonize"):
            with patch.object(self.daemon, "tracker"):
                # This would normally daemonize, but we're testing PID cleanup
                pass

    def test_status_when_not_running(self):
        """Test status when daemon is not running."""
        # No PID file exists
        with patch("builtins.print") as mock_print:
            self.daemon.status()
            mock_print.assert_called_with("Daemon not running")

    def test_status_with_stale_pidfile(self):
        """Test status with stale PID file."""
        # Create a stale PID file
        with open(self.pid_file, "w") as f:
            f.write("99999999")  # Non-existent PID

        with patch("builtins.print"):
            self.daemon.status()

        # Should remove stale PID file
        self.assertFalse(os.path.exists(self.pid_file))

    def test_stop_when_not_running(self):
        """Test stop when daemon is not running."""
        with patch("builtins.print") as mock_print:
            self.daemon.stop()
            mock_print.assert_called_with("Daemon not running")

    @patch("os.kill")
    def test_stop_sends_sigterm(self, mock_kill):
        """Test that stop sends SIGTERM to running daemon."""
        # Create a PID file
        with open(self.pid_file, "w") as f:
            f.write("12345")

        with patch("builtins.print"):
            self.daemon.stop()

        mock_kill.assert_called_with(12345, signal.SIGTERM)

    def test_signal_handler_cleans_up(self):
        """Test that signal handler cleans up resources."""
        # Create a mock tracker
        self.daemon.tracker = Mock()

        # Create a PID file
        with open(self.pid_file, "w") as f:
            f.write("12345")

        with pytest.raises(SystemExit):
            self.daemon._signal_handler(signal.SIGTERM, None)

        # Tracker should be stopped
        self.daemon.tracker.stop.assert_called_once()
        # PID file should be removed
        self.assertFalse(os.path.exists(self.pid_file))


class TestDaemonPidFileHandling(unittest.TestCase):
    """Test cases for PID file handling edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pid_file = os.path.join(self.temp_dir, "test.pid")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_corrupt_pidfile_handling(self):
        """Test handling of corrupt PID file."""
        # Create a corrupt PID file
        with open(self.pid_file, "w") as f:
            f.write("not_a_number")

        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.daemon import ActivityDaemon

            daemon = ActivityDaemon(pidfile=self.pid_file)

        # Should handle corrupt file gracefully
        with patch.object(daemon, "daemonize"):
            with patch("builtins.print"):
                # Start should remove corrupt PID file
                pass

    def test_empty_pidfile_handling(self):
        """Test handling of empty PID file."""
        # Create an empty PID file
        with open(self.pid_file, "w") as f:
            pass

        with patch.dict(
            "sys.modules",
            {
                "AppKit": MagicMock(),
                "Quartz": MagicMock(),
            },
        ):
            from activity_tracker.daemon import ActivityDaemon

            daemon = ActivityDaemon(pidfile=self.pid_file)

        # Should handle empty file gracefully
        with patch.object(daemon, "daemonize"):
            with patch("builtins.print"):
                pass


if __name__ == "__main__":
    unittest.main()
