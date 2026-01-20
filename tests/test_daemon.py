"""Tests for daemon module functionality."""

import os
import signal
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestActivityDaemon(unittest.TestCase):
    """Test cases for ActivityDaemon class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pid_file = os.path.join(self.temp_dir, "test.pid")

        # Patch os.kill globally for this test class to prevent accidental kills
        self.kill_patcher = patch("os.kill")
        self.mock_kill = self.kill_patcher.start()

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
        self.kill_patcher.stop()
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

    @patch("os.fork")
    @patch("os.setsid")
    @patch("os.umask")
    @patch("os.chdir")
    @patch("sys.exit")
    def test_daemonize_success(
        self, mock_exit, mock_chdir, mock_umask, mock_setsid, mock_fork
    ):
        """Test successful daemonization."""
        # Mock forks to return 0 (child process)
        mock_fork.return_value = 0

        with patch("fcntl.flock"):
            self.daemon.daemonize()

        # Should fork twice
        self.assertEqual(mock_fork.call_count, 2)
        mock_setsid.assert_called_once()
        mock_chdir.assert_called_with("/")
        mock_umask.assert_called_with(0o077)
        mock_exit.assert_not_called()

    @patch("os.fork")
    @patch("sys.exit")
    def test_daemonize_parent_exit(self, mock_exit, mock_fork):
        """Test parent exit on first fork."""
        mock_fork.return_value = 123  # Parent
        mock_exit.side_effect = SystemExit

        with self.assertRaises(SystemExit):
            self.daemon.daemonize()

        mock_exit.assert_called_with(0)

    @patch("os.fork")
    @patch("sys.exit")
    def test_daemonize_second_parent_exit(self, mock_exit, mock_fork):
        """Test second parent exit."""
        # First fork returns 0 (child), second fork returns 123 (parent)
        mock_fork.side_effect = [0, 123]
        mock_exit.side_effect = SystemExit

        # We still need to mock os.setsid/chdir/umask because they run BETWEEN forks
        with patch("os.setsid"), patch("os.chdir"), patch("os.umask"):
            with self.assertRaises(SystemExit):
                self.daemon.daemonize()

        mock_exit.assert_called_with(0)

    @patch("os.fork")
    @patch("sys.exit")
    def test_daemonize_fork_error(self, mock_exit, mock_fork):
        """Test handling of fork error."""
        mock_fork.side_effect = OSError("Fork failed")

        with patch("sys.stderr.write"):
            self.daemon.daemonize()

        mock_exit.assert_called_with(1)

    def test_start_already_running(self):
        """Test start when daemon is already running."""
        # Create PID file
        with open(self.pid_file, "w") as f:
            f.write("12345")

        with patch("os.kill") as mock_kill:
            with patch("builtins.print") as mock_print:
                self.daemon.start()

        mock_kill.assert_called_with(12345, 0)
        mock_print.assert_called_with("Daemon already running with PID 12345")

    def test_start_stale_pid(self):
        """Test start with stale PID."""
        with open(self.pid_file, "w") as f:
            f.write("12345")

        # Configure global mock_kill to raise OSError (process not found)
        self.mock_kill.side_effect = OSError

        with patch.object(self.daemon, "daemonize") as mock_daemonize:
            # Patch the class as imported in daemon module
            with patch("activity_tracker.daemon.ActivityTracker") as mock_tracker:
                self.daemon.start()

        # Should remove file and start
        self.assertFalse(os.path.exists(self.pid_file))
        mock_daemonize.assert_called()

    def test_start_corrupt_pid(self):
        """Test start with corrupt PID file."""
        with open(self.pid_file, "w") as f:
            f.write("invalid")

        with patch.object(self.daemon, "daemonize") as mock_daemonize:
            with patch("activity_tracker.daemon.ActivityTracker"):
                self.daemon.start()

        self.assertFalse(os.path.exists(self.pid_file))
        mock_daemonize.assert_called()

    def test_status_when_not_running(self):
        """Test status when daemon is not running."""
        with patch("builtins.print") as mock_print:
            self.daemon.status()
            mock_print.assert_called_with("Daemon not running")

    def test_status_running(self):
        """Test status when running."""
        with open(self.pid_file, "w") as f:
            f.write("12345")

        # Default mock_kill does nothing (success), simulating process exists
        self.mock_kill.side_effect = None

        with patch("builtins.print") as mock_print:
            self.daemon.status()

        mock_print.assert_called_with("Daemon running with PID 12345")

    def test_status_stale(self):
        """Test status with stale PID."""
        with open(self.pid_file, "w") as f:
            f.write("12345")

        # Simulate process not found
        self.mock_kill.side_effect = OSError

        with patch("builtins.print") as mock_print:
            self.daemon.status()

        mock_print.assert_called_with("Daemon not running (stale pidfile)")
        self.assertFalse(os.path.exists(self.pid_file))

    def test_stop_when_not_running(self):
        """Test stop when daemon is not running."""
        with patch("builtins.print") as mock_print:
            self.daemon.stop()
            mock_print.assert_called_with("Daemon not running")

    def test_stop_sends_sigterm(self):
        """Test that stop sends SIGTERM to running daemon."""
        with open(self.pid_file, "w") as _:
            _.write("12345")

        self.mock_kill.side_effect = None

        with patch("builtins.print"):
            self.daemon.stop()

        self.mock_kill.assert_called_with(12345, signal.SIGTERM)

    def test_signal_handler_cleans_up(self):
        """Test that signal handler cleans up resources."""
        self.daemon.tracker = Mock()
        with open(self.pid_file, "w") as _:
            _.write("12345")

        with pytest.raises(SystemExit):
            self.daemon._signal_handler(signal.SIGTERM, None)

        self.daemon.tracker.stop.assert_called_once()
        self.assertFalse(os.path.exists(self.pid_file))

    @patch("activity_tracker.daemon.ActivityDaemon")
    def test_main_commands(self, mock_daemon_class):
        """Test CLI commands."""
        from activity_tracker.daemon import main

        mock_daemon = mock_daemon_class.return_value

        # Test start
        with patch.object(sys, "argv", ["daemon.py", "start"]):
            main()
        mock_daemon.start.assert_called()

        # Test stop
        with patch.object(sys, "argv", ["daemon.py", "stop"]):
            main()
        mock_daemon.stop.assert_called()

        # Test restart
        with patch.object(sys, "argv", ["daemon.py", "restart"]):
            with patch("time.sleep"):
                main()
        mock_daemon.stop.assert_called()
        mock_daemon.start.assert_called()

        # Test status
        with patch.object(sys, "argv", ["daemon.py", "status"]):
            main()
        mock_daemon.status.assert_called()

        # Test unknown
        with patch.object(sys, "argv", ["daemon.py", "unknown"]):
            with self.assertRaises(SystemExit):
                main()


if __name__ == "__main__":
    unittest.main()
