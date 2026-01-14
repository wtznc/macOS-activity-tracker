#!/usr/bin/env python3
"""
Utility functions for macOS Activity Tracker
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def get_data_directory() -> Path:
    """
    Get the appropriate data directory for storing activity data.

    Returns a user-specific directory that works regardless of how the app is launched.
    On macOS, this will be ~/Library/Application Support/ActivityTracker/
    """
    if sys.platform == "darwin":  # macOS
        # Use macOS Application Support directory
        app_support = (
            Path.home() / "Library" / "Application Support" / "ActivityTracker"
        )
    else:
        # Fallback for other platforms
        app_support = Path.home() / ".activity_tracker"

    # Ensure the directory exists
    app_support.mkdir(parents=True, exist_ok=True)
    return app_support


def view_activity_file(filepath):
    """View a single activity file with proper Unicode display."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse filename to get timestamp
        filename = Path(filepath).name
        if filename.startswith("activity_") and filename.endswith(".json"):
            timestamp_str = filename[9:-5]  # Remove 'activity_' and '.json'
            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M")
                print(f"\n[DATE] {dt.strftime('%Y-%m-%d %H:%M')} ({filename})")
            except ValueError:
                print(f"\n[FILE] {filename}")
        else:
            print(f"\n[FILE] {filename}")

        print("=" * 60)

        # Sort by time spent (descending)
        sorted_apps = sorted(data.items(), key=lambda x: x[1], reverse=True)

        total_time = sum(data.values())

        for app_name, duration in sorted_apps:
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            print(f"[TIME] {duration:6.1f}s ({percentage:4.1f}%) - {app_name}")

        print(f"\n[TOTAL] {total_time:.1f} seconds")

    except Exception as e:
        print(f"[ERROR] Error reading {filepath}: {e}")


def main():
    """Main function to view activity data files."""
    if len(sys.argv) < 2:
        print("View Activity Data - Unicode Display")
        print("Usage: python view_data.py <activity_file.json> [file2.json ...]")
        print("\nExample:")
        print("  python view_data.py activity_data/activity_20250622_1524.json")
        print("  python view_data.py activity_data/activity_*.json")
        return

    files = sys.argv[1:]

    # Handle glob patterns
    from glob import glob

    all_files = []
    for pattern in files:
        if "*" in pattern:
            all_files.extend(glob(pattern))
        else:
            all_files.append(pattern)

    # Sort files by name (chronological)
    all_files.sort()

    print(f"[INFO] Viewing {len(all_files)} activity file(s)")

    for filepath in all_files:
        if Path(filepath).exists():
            view_activity_file(filepath)
        else:
            print(f"[ERROR] File not found: {filepath}")


if __name__ == "__main__":
    main()
