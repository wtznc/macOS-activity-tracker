#!/usr/bin/env python3
"""
Data storage and persistence for Pulse.
Handles all file I/O operations and data management.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class ActivityDataStore:
    """Manages storage and retrieval of activity data."""

    def __init__(self, data_dir: str = "activity_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def get_current_minute_filename(self) -> str:
        """Generate filename for current minute."""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M")
        return f"activity_{timestamp}.json"

    def load_existing_data(self, filename: str) -> Dict[str, float]:
        """Load existing data from file."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_data(self, data: Dict[str, float], filename: str) -> None:
        """Save data to file with 2 decimal precision."""
        if not data:
            return

        # Filter out noise values (< 0.01s), then round to 2 decimal places
        rounded_data = {
            app: round(duration, 2)
            for app, duration in data.items()
            if duration >= 0.01
        }

        if not rounded_data:
            return

        filepath = self.data_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rounded_data, f, indent=2, ensure_ascii=False)

    def merge_and_save_session_data(self, session_data: Dict[str, float]) -> None:
        """Merge session data with existing data and save."""
        if not session_data:
            return

        filename = self.get_current_minute_filename()
        existing_data = self.load_existing_data(filename)

        # Merge with current session data (round to 2 decimals)
        for app, duration in session_data.items():
            existing_data[app] = round(existing_data.get(app, 0) + duration, 2)

        self.save_data(existing_data, filename)


class SessionTracker:
    """Tracks activity for the current session."""

    def __init__(self):
        self.current_session: Dict[str, float] = {}

    def add_activity(self, app_name: str, duration: float) -> None:
        """Add activity duration for an application."""
        if app_name and duration > 0:
            self.current_session[app_name] = (
                self.current_session.get(app_name, 0) + duration
            )

    def get_session_data(self) -> Dict[str, float]:
        """Get current session data."""
        return self.current_session.copy()

    def clear_session(self) -> Dict[str, float]:
        """Clear and return current session data."""
        data = self.current_session.copy()
        self.current_session.clear()
        return data

    def get_total_time(self) -> float:
        """Get total time tracked in current session."""
        return sum(self.current_session.values())
