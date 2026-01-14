#!/usr/bin/env python3
"""
Application and window detection for macOS Activity Tracker.
Handles all macOS-specific detection logic.
"""

import subprocess  # nosec B404 - Required for macOS AppleScript integration
import time
from typing import Optional

try:
    from AppKit import NSWorkspace
    from Quartz import (
        CGEventSourceSecondsSinceLastEventType,
        CGWindowListCopyWindowInfo,
        kCGAnyInputEventType,
        kCGEventSourceStateHIDSystemState,
        kCGNullWindowID,
        kCGWindowListOptionOnScreenOnly,
    )
except ImportError:
    print("Error: pyobjc-framework-Cocoa not installed.")
    exit(1)


class ApplicationDetector:
    """Detects currently active applications on macOS."""

    def get_active_application(self) -> Optional[str]:
        """Get the currently active application name."""
        try:
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            if active_app:
                return active_app["NSApplicationName"]
        except Exception as e:
            print(f"Error getting active application: {e}")
        return None


class WindowTitleDetector:
    """Detects window titles for specific applications."""

    APP_MAPPING = {
        "iTerm2": "iTerm2",
        "Terminal": "Terminal",
        "Safari": "Safari",
        "Google Chrome": "Google Chrome",
        "Firefox": "Firefox",
        "Visual Studio Code": "Visual Studio Code",
        "Code": "Visual Studio Code",
        "Xcode": "Xcode",
    }

    def __init__(self, cache_ttl: float = 2.0, applescript_timeout: float = 0.5):
        """
        Initialize the WindowTitleDetector with caching and configurable timeout.

        Args:
            cache_ttl: Time-to-live for cached window titles in seconds.
            applescript_timeout: Timeout for AppleScript calls in seconds.
        """
        self.cache_ttl = cache_ttl
        self.applescript_timeout = applescript_timeout
        self._title_cache: dict[str, tuple[str, float]] = {}
        self._metrics = {
            "total_calls": 0,
            "cache_hits": 0,
            "applescript_calls": 0,
            "applescript_timeouts": 0,
            "applescript_total_time": 0.0,
            "quartz_fallbacks": 0,
        }

    def get_window_title(self, app_name: str) -> Optional[str]:
        """Get the title of the frontmost window for the given application."""
        self._metrics["total_calls"] += 1

        try:
            # Check cache first
            cached_title = self._get_from_cache(app_name)
            if cached_title is not None:
                self._metrics["cache_hits"] += 1
                return cached_title

            # Try AppleScript for supported apps
            if app_name in self.APP_MAPPING:
                title = self._get_title_via_applescript(app_name)
                if title:
                    self._update_cache(app_name, title)
                    return title
                # AppleScript failed/timed out - fallback to Quartz
                self._metrics["quartz_fallbacks"] += 1

            # Use Quartz for unsupported apps or as fallback
            title = self._get_title_via_quartz(app_name, count_as_fallback=False)
            if title:
                self._update_cache(app_name, title)
            return title

        except Exception as e:
            print(f"Warning: Failed to get window title for {app_name}: {e}")
        return None

    def _get_from_cache(self, app_name: str) -> Optional[str]:
        """Get window title from cache if not expired."""
        if app_name in self._title_cache:
            title, timestamp = self._title_cache[app_name]
            if time.time() - timestamp < self.cache_ttl:
                return title
            # Remove expired entry
            del self._title_cache[app_name]
        return None

    def _update_cache(self, app_name: str, title: str) -> None:
        """Update cache with new window title."""
        self._title_cache[app_name] = (title, time.time())

    def get_metrics(self) -> dict:
        """Get performance metrics for AppleScript calls."""
        metrics = self._metrics.copy()
        if metrics["applescript_calls"] > 0:
            metrics["avg_applescript_time"] = (
                metrics["applescript_total_time"] / metrics["applescript_calls"]
            )
        else:
            metrics["avg_applescript_time"] = 0.0
        return metrics

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._metrics = {
            "total_calls": 0,
            "cache_hits": 0,
            "applescript_calls": 0,
            "applescript_timeouts": 0,
            "applescript_total_time": 0.0,
            "quartz_fallbacks": 0,
        }

    def _get_title_via_applescript(self, app_name: str) -> Optional[str]:
        """Get window title using AppleScript with timeout and metrics."""
        if app_name in ["Visual Studio Code", "Code"]:
            script = (
                'tell application "System Events"\n'
                "try\n"
                'if exists process "Code" then\n'
                'set frontWindow to front window of process "Code"\n'
                "return title of frontWindow\n"
                "end if\n"
                "end try\n"
                "end tell\n"
                'return ""'
            )
        else:
            mapped_name = self.APP_MAPPING[app_name]
            script = (
                f'tell application "{mapped_name}"\n'
                "try\n"
                "if (count of windows) > 0 then\n"
                "return name of front window\n"
                "end if\n"
                "end try\n"
                "end tell\n"
                'return ""'
            )

        try:
            self._metrics["applescript_calls"] += 1
            start_time = time.time()

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=self.applescript_timeout,
            )

            elapsed = time.time() - start_time
            self._metrics["applescript_total_time"] += elapsed

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self._metrics["applescript_timeouts"] += 1
            # Fallback to Quartz will be handled by the caller
            pass

        return None

    def _get_title_via_quartz(
        self, app_name: str, count_as_fallback: bool = True
    ) -> Optional[str]:
        """Get window title using Quartz framework."""
        if count_as_fallback:
            self._metrics["quartz_fallbacks"] += 1
        try:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly, kCGNullWindowID
            )

            for window in window_list:
                owner_name = window.get("kCGWindowOwnerName", "")
                if owner_name == app_name:
                    window_title = window.get("kCGWindowName", "")
                    if window_title and window_title.strip():
                        return window_title

            # Special handling for VS Code
            if app_name in ["Code", "Visual Studio Code"]:
                return self._get_vscode_fallback_title(window_list)

        except Exception as e:
            print(f"Warning: Failed to get window title: {e}")

        return None

    def _get_vscode_fallback_title(self, window_list) -> Optional[str]:
        """Fallback method for VS Code window detection."""
        for window in window_list:
            owner_name = window.get("kCGWindowOwnerName", "")
            if owner_name in ["Code", "Visual Studio Code"]:
                window_layer = window.get("kCGWindowLayer", 0)
                window_bounds = window.get("kCGWindowBounds", {})
                if (
                    window_layer == 0
                    and window_bounds.get("Width", 0) > 200
                    and window_bounds.get("Height", 0) > 200
                ):
                    return "Editor Window"
        return None


class IdleDetector:
    """Detects system idle state on macOS."""

    def __init__(self, idle_threshold: int = 300):
        self.idle_threshold = idle_threshold
        self.is_idle = False
        self.idle_start_time: Optional[float] = None

    def get_system_idle_time(self) -> float:
        """Get system idle time in seconds."""
        try:
            return CGEventSourceSecondsSinceLastEventType(
                kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
            )
        except Exception as e:
            print(f"Error getting system idle time: {e}")
            return 0.0

    def check_idle_state(self) -> bool:
        """Check if system is currently idle."""
        idle_time = self.get_system_idle_time()
        current_time = time.time()

        if idle_time >= self.idle_threshold:
            if not self.is_idle:
                self.is_idle = True
                self.idle_start_time = current_time
                return True  # Just became idle
            return False  # Already idle
        else:
            if self.is_idle:
                self.is_idle = False
                self.idle_start_time = None
                return True  # Just became active
            return False  # Already active

    def get_idle_transition_info(self) -> tuple[bool, Optional[float]]:
        """Get idle state and time information for activity recording."""
        idle_time = self.get_system_idle_time()
        current_time = time.time()

        if idle_time >= self.idle_threshold and not self.is_idle:
            # Just became idle - calculate when we actually went idle
            idle_start_timestamp = current_time - idle_time
            return True, idle_start_timestamp

        return self.is_idle, None


class TitleCleaner:
    """Cleans and normalizes window titles."""

    UNICODE_REPLACEMENTS = {
        "\u201c": '"',  # Left double quotation mark
        "\u201d": '"',  # Right double quotation mark
        "\u2018": "'",  # Left single quotation mark
        "\u2019": "'",  # Right single quotation mark
        "\u00b7": "·",  # Middle dot
        "\u2022": "•",  # Bullet point
        "\u2026": "…",  # Horizontal ellipsis
        "\u2013": "–",  # En dash
        "\u2014": "—",  # Em dash
        "\u2733": "*",  # Eight spoked asterisk
        "\u25cf": "*",  # Black circle
        "\u25cb": "o",  # White circle
        "\u2713": "+",  # Check mark
        "\u2717": "x",  # Ballot X
    }

    def clean_title(self, title: str) -> str:
        """Clean up window title by properly handling Unicode characters."""
        if not title:
            return title

        # Normalize Unicode
        try:
            import unicodedata

            title = unicodedata.normalize("NFC", title)
        except Exception as e:
            print(f"Warning: Failed to normalize Unicode in title: {e}")

        # Apply replacements
        for unicode_char, replacement in self.UNICODE_REPLACEMENTS.items():
            title = title.replace(unicode_char, replacement)

        # VS Code specific cleaning
        if title.endswith(" — Visual Studio Code"):
            title = title[:-21]
        elif title.endswith(" - Visual Studio Code"):
            title = title[:-20]

        return title

    def normalize_app_name(self, app_with_window: str) -> str:
        """Normalize app name to handle temporary states."""
        if not app_with_window:
            return app_with_window

        app_name = app_with_window.split(" - ")[0]

        if " - osascript" in app_with_window or " - AppleScript" in app_with_window:
            return app_name

        return app_with_window
