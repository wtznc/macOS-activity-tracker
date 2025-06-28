#!/usr/bin/env python3
"""
macOS Activity Tracker Daemon
Tracks time spent on applications and websites in the background.
"""

import time
from datetime import datetime
from typing import Optional

from .activity_monitor import ActivityLogger, ActivityMonitor
from .storage import ActivityDataStore
from .utils import get_data_directory


class ActivityTracker:
    """
    macOS Activity Tracker - Orchestrates activity monitoring components.

    Uses composition to delegate responsibilities to specialized classes,
    following the Single Responsibility Principle.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        interval: int = 60,
        verbose: bool = True,
        include_window_titles: bool = True,
        fast_mode: bool = False,
        idle_threshold: int = 300,
    ):
        """
        Initialize the Activity Tracker.

        Args:
            data_dir (Optional[str]): Directory to store activity data files. 
                                    If None, uses appropriate user data directory.
            interval (int): Data save interval in seconds.
            verbose (bool): Enable verbose logging of app switches.
            include_window_titles (bool): Include window titles in tracking.
            fast_mode (bool): Enable fast mode (app names only, no window titles).
            idle_threshold (int): Idle detection threshold in seconds.
        """
        self.interval = interval
        self.running = False
        self.last_check_time = datetime.now()

        # Use appropriate data directory
        if data_dir is None:
            data_dir = str(get_data_directory())

        # Use composition - inject specialized components
        window_titles = include_window_titles and not fast_mode
        debounce_delay = 1.0 if window_titles else 0.3

        self.monitor = ActivityMonitor(
            include_window_titles=window_titles,
            idle_threshold=idle_threshold,
            debounce_delay=debounce_delay,
        )
        self.logger = ActivityLogger(verbose=verbose)
        self.data_store = ActivityDataStore(data_dir)

    def track_activity(self):
        """Main tracking loop - orchestrates all components."""
        current_app = None
        start_time = time.time()

        self.logger.log_tracking_start(self.monitor.include_window_titles)

        while self.running:
            try:
                # Check for idle state changes

                # Handle idle state transitions
                if self.monitor.idle_detector.check_idle_state():
                    if self.monitor.idle_detector.is_idle:
                        time.sleep(1.0)  # Check idle state less frequently
                        continue

                # Handle idle transition timing
                start_time = self.monitor.handle_idle_transition(
                    current_app, start_time
                )

                # Get current activity with timing
                active_app = self.monitor.get_current_activity()

                # Handle app changes with debouncing
                current_app, start_time = self.monitor.check_app_change(
                    current_app, active_app, start_time
                )

                # Initialize current app if needed
                if not current_app and active_app:
                    current_app = active_app
                    start_time = time.time()
                    self.logger.log_initial_app(active_app)

                # Check for data save interval
                self._check_save_interval(current_app, start_time)

                time.sleep(0.5)  # Reduced to 500ms for better responsiveness

            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"Error in tracking loop: {e}")
                time.sleep(5)

        # Save any remaining data
        self._save_final_data(current_app, start_time)
        self.logger.log_tracking_stop()

    def _check_save_interval(self, current_app: Optional[str], start_time: float):
        """Check if we need to save data (every minute)."""
        now = datetime.now()
        if now.minute != self.last_check_time.minute:
            # Record time for current app before saving
            if current_app:
                duration = time.time() - start_time
                self.monitor.session_tracker.add_activity(current_app, duration)

            # Save and clear session data
            session_data = self.monitor.clear_session_data()
            self.data_store.merge_and_save_session_data(session_data)

            total_time = sum(session_data.values())
            self.logger.log_data_save(total_time)

            self.last_check_time = now

    def _save_final_data(self, current_app: Optional[str], start_time: float):
        """Save any remaining session data before exit."""
        if current_app:
            duration = time.time() - start_time
            self.monitor.session_tracker.add_activity(current_app, duration)

        session_data = self.monitor.clear_session_data()
        self.data_store.merge_and_save_session_data(session_data)

    def start(self):
        """Start the activity tracker."""
        print(
            f"Starting activity tracker... "
            f"Data will be saved to {self.data_store.data_dir}"
        )
        idle_minutes = self.monitor.idle_detector.idle_threshold // 60
        print(
            f"AFK detection: Will pause tracking after "
            f"{idle_minutes} minutes of inactivity"
        )
        self.running = True
        self.track_activity()

    def stop(self):
        """Stop the activity tracker."""
        print("Stopping activity tracker...")
        self.running = False


def main():
    """Main entry point."""
    import sys

    # Parse command line arguments
    verbose = True
    fast_mode = False
    include_window_titles = True
    idle_threshold = 300  # 5 minutes default

    if "--quiet" in sys.argv or "-q" in sys.argv:
        verbose = False
    if "--fast" in sys.argv or "-f" in sys.argv:
        fast_mode = True
        include_window_titles = False
    if "--no-windows" in sys.argv:
        include_window_titles = False

    # Parse idle threshold
    for i, arg in enumerate(sys.argv):
        if arg == "--idle-threshold" and i + 1 < len(sys.argv):
            try:
                idle_threshold = int(sys.argv[i + 1])
            except ValueError:
                print(f"Invalid idle threshold: {sys.argv[i + 1]}")
                return

    if "--help" in sys.argv or "-h" in sys.argv:
        print("macOS Activity Tracker")
        print("Usage: python activity_tracker.py [options]")
        print("Options:")
        print("  --quiet, -q            Run in quiet mode (no logging)")
        print("  --fast, -f             Fast mode (app names only, no window titles)")
        print("  --no-windows           Disable window title detection")
        print(
            "  --idle-threshold SEC   AFK detection threshold in seconds (default: 300)"
        )
        print("  --help, -h             Show this help message")
        return

    tracker = ActivityTracker(
        verbose=verbose,
        fast_mode=fast_mode,
        include_window_titles=include_window_titles,
        idle_threshold=idle_threshold,
    )

    try:
        tracker.start()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
    finally:
        tracker.stop()
        print("Activity tracker stopped")


if __name__ == "__main__":
    main()
