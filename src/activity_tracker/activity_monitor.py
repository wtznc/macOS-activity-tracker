#!/usr/bin/env python3
"""
Activity monitoring core logic for macOS Activity Tracker.
Orchestrates detection, idle checking, and data recording.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from .detection import (
    ApplicationDetector,
    IdleDetector,
    TitleCleaner,
    WindowTitleDetector,
)
from .storage import SessionTracker


@dataclass
class MonitorConfig:
    """Configuration for ActivityMonitor."""

    include_window_titles: bool = True
    idle_threshold: int = 300
    debounce_delay: float = 1.0
    max_duration_cap: float = 120.0  # Cap for single activity segments


class ActivityMonitor:
    """Core activity monitoring logic with single responsibility."""

    def __init__(
        self,
        include_window_titles: bool = True,
        idle_threshold: int = 300,
        debounce_delay: float = 1.0,
        app_detector: Optional[ApplicationDetector] = None,
        idle_detector: Optional[IdleDetector] = None,
        window_detector: Optional[WindowTitleDetector] = None,
    ):
        self.config = MonitorConfig(
            include_window_titles=include_window_titles,
            idle_threshold=idle_threshold,
            debounce_delay=debounce_delay,
        )

        # Composition - allow dependency injection
        self.app_detector = app_detector or ApplicationDetector()
        self.idle_detector = idle_detector or IdleDetector(self.config.idle_threshold)

        self.window_detector: Optional[WindowTitleDetector] = None
        if self.config.include_window_titles:
            self.window_detector = window_detector or WindowTitleDetector()

        self.title_cleaner = TitleCleaner()
        self.session_tracker = SessionTracker()

        # State for debouncing
        self.last_stable_app: Optional[str] = None
        self.app_change_time: Optional[float] = None

    @property
    def include_window_titles(self) -> bool:
        return self.config.include_window_titles

    @property
    def debounce_delay(self) -> float:
        return self.config.debounce_delay

    def get_current_activity(self) -> Optional[str]:
        """Get current activity (app or app + window title)."""
        app_name = self.app_detector.get_active_application()
        if not app_name:
            return None

        if not self.window_detector:
            return app_name

        window_title = self.window_detector.get_window_title(app_name)
        if window_title:
            clean_title = self.title_cleaner.clean_title(window_title)
            full_name = f"{app_name} - {clean_title}"
            return self.title_cleaner.normalize_app_name(full_name)

        return app_name

    def should_record_activity(self) -> bool:
        """Check if system is active and should record activity."""
        return not self.idle_detector.is_idle

    def handle_idle_transition(
        self, current_app: Optional[str], start_time: float
    ) -> float:
        """
        Handle idle state transitions and return new start time.

        If we transitioned to IDLE, we attempt to record the activity
        that happened *before* the idle threshold was reached.
        """
        # Check if idle state changed
        idle_state_changed = self.idle_detector.check_idle_state()

        if not idle_state_changed:
            return start_time

        current_time = time.time()

        if self.idle_detector.is_idle:
            # Just became idle.
            # We need to calculate how much valid activity occurred before idleness.
            if current_app:
                idle_time = self.idle_detector.get_system_idle_time()
                # Timestamp when idleness actually began
                idle_start_timestamp = current_time - idle_time

                # Duration from the tracked start_time until idleness began
                active_duration = idle_start_timestamp - start_time

                # We only record if this duration is positive.
                # It might be negative if start_time was reset (e.g. by minute boundary)
                # *after* the user actually went idle.
                if 0 < active_duration <= self.config.max_duration_cap:
                    self.session_tracker.add_activity(current_app, active_duration)

            return current_time
        else:
            # Just became active - return current time as new start
            return current_time

    def check_app_change(
        self, current_app: Optional[str], active_app: Optional[str], start_time: float
    ) -> Tuple[Optional[str], float]:
        """
        Handle application change detection with debouncing.
        Returns tuple of (current_stable_app, start_time_of_that_app).
        """
        current_time = time.time()

        if self.last_stable_app != active_app:
            if self.app_change_time is None:
                self.app_change_time = current_time
            elif current_time - self.app_change_time >= self.config.debounce_delay:
                # App switch confirmed (stabilized for debounce_delay)

                # Record the *previous* app's duration
                if current_app and current_app != active_app:
                    duration = current_time - start_time
                    if 0 < duration <= self.config.max_duration_cap:
                        self.session_tracker.add_activity(current_app, duration)

                self.last_stable_app = active_app
                self.app_change_time = None
                return active_app, current_time
        else:
            self.app_change_time = None

        return current_app, start_time

    def get_session_total_time(self) -> float:
        """Get total time tracked in current session."""
        return self.session_tracker.get_total_time()

    def clear_session_data(self) -> dict:
        """Clear and return current session data."""
        return self.session_tracker.clear_session()


class ActivityLogger:
    """Handles logging and output for activity tracking."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log_tracking_start(self, include_window_titles: bool) -> None:
        """Log tracking start information."""
        if not self.verbose:
            return

        print("Tracking started - watching for app switches...")
        mode = (
            "detailed mode (app + window titles)"
            if include_window_titles
            else "fast mode (app names only)"
        )
        print(f"Mode: {mode}")
        print("Format: [HH:MM:SS] App Switch: Previous App (duration) -> New App")
        print("-" * 70)

    def log_app_switch(
        self, old_app: str, duration: float, new_app: str, detection_time: float
    ) -> None:
        """Log application switch."""
        if not self.verbose:
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] Switch: {old_app} ({duration:.1f}s) -> {new_app}")

        if detection_time > 100:
            print(f"  [WARN] Slow detection: {detection_time:.0f}ms")

    def log_initial_app(self, app_name: str) -> None:
        """Log initial application detection."""
        if not self.verbose:
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] Initial app: {app_name}")

    def log_idle_detected(self, idle_time: float) -> None:
        """Log idle state detection."""
        if not self.verbose:
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{now_str}] [IDLE] User idle detected "
            f"(no input for {idle_time:.0f}s) - pausing tracking"
        )

    def log_activity_resumed(self, idle_duration: float) -> None:
        """Log activity resumption."""
        if not self.verbose:
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{now_str}] [ACTIVE] User activity resumed "
            f"(was idle for {idle_duration:.0f}s) - resuming tracking"
        )

    def log_data_save(self, total_time: float) -> None:
        """Log data save operation."""
        if not self.verbose:
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] Minute boundary - saving {total_time:.1f}s of data")

    def log_tracking_stop(self) -> None:
        """Log tracking stop."""
        if self.verbose:
            print("\nTracking stopped")
