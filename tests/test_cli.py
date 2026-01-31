"""Tests for CLI entry point."""

import sys
import unittest
from unittest.mock import patch

from pulse.core import main


class TestCLI(unittest.TestCase):
    """Test cases for CLI arguments and main execution."""

    @patch("pulse.core.Pulse")
    def test_main_defaults(self, mock_tracker_class):
        """Test main with default arguments."""
        mock_tracker = mock_tracker_class.return_value

        with patch.object(sys, "argv", ["pulse"]):
            main()

        mock_tracker_class.assert_called_with(
            verbose=True,
            fast_mode=False,
            include_window_titles=True,
            idle_threshold=300,
        )
        mock_tracker.start.assert_called()
        mock_tracker.stop.assert_called()

    @patch("pulse.core.Pulse")
    def test_main_arguments(self, mock_tracker_class):
        """Test main with various arguments."""
        args = ["pulse", "--quiet", "--fast", "--idle-threshold", "600"]

        with patch.object(sys, "argv", args):
            main()

        mock_tracker_class.assert_called_with(
            verbose=False,
            fast_mode=True,
            include_window_titles=False,
            idle_threshold=600,
        )

    @patch("pulse.core.Pulse")
    def test_main_no_windows(self, mock_tracker_class):
        """Test main with --no-windows."""
        with patch.object(sys, "argv", ["pulse", "--no-windows"]):
            main()

        mock_tracker_class.assert_called_with(
            verbose=True,
            fast_mode=False,
            include_window_titles=False,
            idle_threshold=300,
        )

    @patch("pulse.core.Pulse")
    def test_main_invalid_idle(self, mock_tracker_class):
        """Test main with invalid idle threshold."""
        with patch.object(sys, "argv", ["pulse", "--idle-threshold", "invalid"]):
            with patch("builtins.print") as mock_print:
                main()

        mock_print.assert_called_with("Invalid idle threshold: invalid")
        mock_tracker_class.assert_not_called()

    def test_main_help(self):
        """Test help argument."""
        with patch.object(sys, "argv", ["pulse", "--help"]):
            with patch("builtins.print") as mock_print:
                main()

        # Should print help and exit
        self.assertTrue(mock_print.called)
        # Should verify some help text
        args, _ = mock_print.call_args_list[0]
        self.assertEqual(args[0], "Pulse")

    @patch("pulse.core.Pulse")
    def test_main_interrupt(self, mock_tracker_class):
        """Test keyboard interrupt handling."""
        mock_tracker = mock_tracker_class.return_value
        mock_tracker.start.side_effect = KeyboardInterrupt

        with patch.object(sys, "argv", ["pulse"]):
            with patch("builtins.print") as mock_print:
                main()

        mock_print.assert_any_call("\nReceived interrupt signal")
        mock_tracker.stop.assert_called()
