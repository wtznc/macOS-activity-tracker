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
        except (KeyError, AttributeError, RuntimeError) as e:
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

    def get_window_title(self, app_name: str) -> Optional[str]:
        """Get the title of the frontmost window for the given application."""
        try:
            if app_name in self.APP_MAPPING:
                title = self._get_title_via_applescript(app_name)
                if title:
                    return title

            return self._get_title_via_quartz(app_name)

        except (subprocess.SubprocessError, KeyError, TypeError, RuntimeError) as e:
            print(f"Warning: Failed to get window title for {app_name}: {e}")
        return None

    def _get_title_via_applescript(self, app_name: str) -> Optional[str]:
        """Get window title using AppleScript."""
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
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=1.0
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except subprocess.TimeoutExpired:
            pass

        return None

    def _get_title_via_quartz(self, app_name: str) -> Optional[str]:
        """Get window title using Quartz framework."""
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

        except (KeyError, TypeError, RuntimeError) as e:
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
        except (RuntimeError, OSError) as e:
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
        except (TypeError, ValueError) as e:
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
