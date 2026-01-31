#!/usr/bin/env python3
"""
Data aggregation for Pulse sync functionality.
Handles grouping and processing of activity data files.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ActivityFileParser:
    """Parses activity filenames and extracts datetime information."""

    @staticmethod
    def parse_filename(filename: str) -> Optional[datetime]:
        """Parse activity filename to get datetime."""
        match = re.match(r"activity_(\d{8})_(\d{4})\.json", filename)
        if match:
            date_str, time_str = match.groups()
            try:
                return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M")
            except ValueError:
                return None
        return None

    @staticmethod
    def get_hour_key(dt: datetime) -> str:
        """Convert datetime to hour key format."""
        return dt.strftime("%Y-%m-%d_%H")


class DataAggregator:
    """Aggregates activity data from multiple files."""

    def __init__(self, data_dir: str = "activity_data"):
        self.data_dir = Path(data_dir)
        self.file_parser = ActivityFileParser()

    def group_files_by_hour(self) -> Dict[str, List[Path]]:
        """Group activity files by hour."""
        if not self.data_dir.exists():
            return {}

        files_by_hour: Dict[str, List[Path]] = {}

        for file_path in self.data_dir.glob("activity_*.json"):
            dt = self.file_parser.parse_filename(file_path.name)
            if dt:
                hour_key = self.file_parser.get_hour_key(dt)
                if hour_key not in files_by_hour:
                    files_by_hour[hour_key] = []
                files_by_hour[hour_key].append(file_path)

        return files_by_hour

    def aggregate_hour_data(self, file_paths: List[Path]) -> Dict:
        """Aggregate data from multiple files into single hour summary."""
        aggregated: Dict[str, float] = {}
        total_files = 0

        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total_files += 1

                    for app, duration in data.items():
                        aggregated[app] = aggregated.get(app, 0) + duration
            except (json.JSONDecodeError, IOError, PermissionError) as e:
                print(f"Warning: Could not read {file_path}: {e}")

        return {
            "applications": aggregated,
            "total_time": sum(aggregated.values()),
            "files_processed": total_files,
        }

    def get_all_aggregated_data(self) -> Dict[str, Dict]:
        """Get all data aggregated by hour."""
        files_by_hour = self.group_files_by_hour()
        aggregated_data = {}

        for hour_key, file_paths in files_by_hour.items():
            aggregated_data[hour_key] = self.aggregate_hour_data(file_paths)

        return aggregated_data


class SyncStateManager:
    """Manages sync state and tracks what has been synced."""

    def __init__(self, data_dir: str = "activity_data"):
        self.data_dir = Path(data_dir)
        self.synced_hours_file = self.data_dir / "synced_hours.json"
        self.synced_hours = self._load_synced_hours()

    def _load_synced_hours(self) -> set:
        """Load list of already synced hours."""
        try:
            if self.synced_hours_file.exists():
                with open(self.synced_hours_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            else:
                return set()
        except (json.JSONDecodeError, IOError, PermissionError):
            return set()

    def save_synced_hours(self):
        """Save list of synced hours."""
        try:
            with open(self.synced_hours_file, "w", encoding="utf-8") as f:
                json.dump(list(self.synced_hours), f, ensure_ascii=False)
        except (IOError, PermissionError) as e:
            print(f"Warning: Could not save synced hours: {e}")

    def is_hour_synced(self, hour_key: str) -> bool:
        """Check if hour has been synced."""
        return hour_key in self.synced_hours

    def mark_hour_synced(self, hour_key: str):
        """Mark hour as synced."""
        self.synced_hours.add(hour_key)
        self.save_synced_hours()

    def get_pending_hours(self, available_hours: List[str]) -> List[str]:
        """Get list of hours that haven't been synced yet."""
        return [hour for hour in available_hours if hour not in self.synced_hours]

    def get_sync_statistics(self, available_hours: List[str]) -> Dict:
        """Get sync statistics."""
        total_hours = len(available_hours)
        synced_hours = len(self.synced_hours.intersection(available_hours))
        pending_hours = total_hours - synced_hours

        return {
            "total_hours": total_hours,
            "synced_hours": synced_hours,
            "pending_hours": pending_hours,
            "last_sync": max(self.synced_hours) if self.synced_hours else None,
        }
