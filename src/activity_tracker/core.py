#!/usr/bin/env python3
"""
macOS Activity Tracker Daemon
Tracks time spent on applications and websites in the background.
"""

import time
from datetime import datetime
from typing import Optional

from .activity_monitor import ActivityLogger, ActivityMonitor
from .config import DEFAULT_CONFIG
from .storage import ActivityDataStore
from .utils import get_data_directory

# Maximum allowed total time per minute interval (in seconds).
# Set to 65 to allow slight overflow due to timing imprecision between
# app switches, polling intervals, and minute boundary detection.
# If total exceeds this threshold, durations are proportionally scaled to 60s.
MAX_MINUTE_TOTAL_SECONDS = 65


class ActivityTracker:
    """
    macOS Activity Tracker - Orchestrates activity monitoring components.

    Uses composition to delegate responsibilities to specialized classes,
    following the Single Responsibility Principle.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        interval: int = DEFAULT_CONFIG["save_interval"],
        verbose: bool = DEFAULT_CONFIG["verbose_logging"],
        include_window_titles: bool = DEFAULT_CONFIG["include_window_titles"],
        fast_mode: bool = DEFAULT_CONFIG["fast_mode"],
        idle_threshold: int = DEFAULT_CONFIG["idle_threshold"],
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

                # Check for data save interval and update start_time
                start_time = self._check_save_interval(current_app, start_time)

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

    def _check_save_interval(
        self, current_app: Optional[str], start_time: float
    ) -> float:
        """Check if we need to save data (every minute). Returns updated start_time."""
        now = datetime.now()
        if now.minute != self.last_check_time.minute:
            # Get and clear existing session data
            existing_session_data = self.monitor.clear_session_data()

            # Calculate time attribution for current app
            time_since_boundary = 0.0
            if current_app:
                time_since_boundary = self._calculate_time_in_current_minute(
                    start_time, self.last_check_time
                )
                time_since_boundary = max(
                    0.0, min(time_since_boundary, 60.0)
                )  # Bound to [0, 60]

            # Create data for this minute with proper time bounds
            minute_bounded_data = {}

            # Include existing session data but bound it to prevent overflow
            last_boundary_timestamp = self.last_check_time.timestamp()
            current_timestamp = time.time()
            max_possible_time = current_timestamp - last_boundary_timestamp
            max_reasonable_time = min(60.0, max_possible_time)

            for app_name, duration in existing_session_data.items():
                # For non-current apps, use existing duration but cap it
                if app_name != current_app:
                    bounded_duration = min(duration, max_reasonable_time)
                    if bounded_duration > 0:
                        minute_bounded_data[app_name] = bounded_duration
                else:
                    # For current app, replace with time since boundary
                    if time_since_boundary > 0:
                        minute_bounded_data[app_name] = time_since_boundary

            # Add current app if not already processed
            if (
                current_app
                and current_app not in minute_bounded_data
                and time_since_boundary > 0
            ):
                minute_bounded_data[current_app] = time_since_boundary

            # Final safety check: ensure total doesn't exceed reasonable bounds
            total_time = sum(minute_bounded_data.values())
            if total_time > MAX_MINUTE_TOTAL_SECONDS:
                # Proportionally scale down all durations
                scale_factor = 60.0 / total_time
                minute_bounded_data = {
                    app: duration * scale_factor
                    for app, duration in minute_bounded_data.items()
                }
                total_time = sum(minute_bounded_data.values())

            # Save the properly bounded data
            self.data_store.merge_and_save_session_data(minute_bounded_data)
            self.logger.log_data_save(total_time)

            self.last_check_time = now
            # Reset start_time to prevent accumulation across minute boundaries
            return time.time()

        return start_time

    def _calculate_time_in_current_minute(
        self, start_time: float, last_boundary: datetime
    ) -> float:
        """Calculate how much time should be attributed to the current minute only."""
        current_time = time.time()
        last_boundary_timestamp = last_boundary.timestamp()

        # If start_time is before the last minute boundary, only count time since boundary
        if start_time < last_boundary_timestamp:
            return current_time - last_boundary_timestamp
        else:
            # If start_time is after boundary, count full duration
            return current_time - start_time

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
