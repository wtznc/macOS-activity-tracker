#!/usr/bin/env python3
"""
Sync Manager for Pulse
Orchestrates data aggregation and HTTP synchronization.
"""

from typing import Dict, Optional

from .data_aggregator import DataAggregator, SyncStateManager
from .http_sync import DeviceIdentifier, HttpSyncClient, SyncResultCollector


class SyncManager:
    """Orchestrates data aggregation and HTTP synchronization."""

    def __init__(
        self,
        data_dir: str = "activity_data",
        endpoint: str = "",
        auth_token: str = "",  # nosec B107
    ):
        self.endpoint = endpoint
        self.auth_token = auth_token

        # Use composition - inject specialized components
        self.data_aggregator = DataAggregator(data_dir)
        self.sync_state = SyncStateManager(data_dir)
        self.http_client = HttpSyncClient(endpoint, auth_token)
        self.device_identifier = DeviceIdentifier()

    def sync_hour(self, hour_key: str, hour_data: Dict, force: bool = False) -> bool:
        """Sync single hour of data to endpoint."""
        if not self.endpoint:
            print("Error: No sync endpoint configured.")
            return False

        if not force and self.sync_state.is_hour_synced(hour_key):
            print(f"Hour {hour_key} already synced (use force=True to resync)")
            return True

        success = self.http_client.sync_hour_data(hour_key, hour_data)
        if success:
            self.sync_state.mark_hour_synced(hour_key)

        return success

    def sync_all(self, force: bool = False, max_hours: Optional[int] = None) -> Dict:
        """Sync all available data."""
        if not self.endpoint:
            print("Error: No sync endpoint configured.")
            print(
                "Set PULSE_ENDPOINT environment variable or "
                "provide endpoint parameter."
            )
            return {"synced": 0, "failed": 0, "skipped": 0}

        files_by_hour = self.data_aggregator.group_files_by_hour()

        if not files_by_hour:
            print("No activity files found to sync")
            return {"synced": 0, "failed": 0, "skipped": 0}

        result_collector = SyncResultCollector()
        sorted_hours = sorted(files_by_hour.keys())

        if max_hours:
            sorted_hours = sorted_hours[-max_hours:]

        print(f"Syncing {len(sorted_hours)} hours of data...")

        for hour_key in sorted_hours:
            if not force and self.sync_state.is_hour_synced(hour_key):
                result_collector.record_sync_skip()
                continue

            file_paths = files_by_hour[hour_key]
            hour_data = self.data_aggregator.aggregate_hour_data(file_paths)

            if self.sync_hour(hour_key, hour_data, force):
                result_collector.record_sync_success()
            else:
                result_collector.record_sync_failure()

        return result_collector.get_results()

    def get_sync_status(self) -> Dict:
        """Get current sync status."""
        files_by_hour = self.data_aggregator.group_files_by_hour()
        available_hours = list(files_by_hour.keys())

        stats = self.sync_state.get_sync_statistics(available_hours)
        stats.update(
            {
                "endpoint": self.endpoint,
                "device": self.device_identifier.get_device_name(),
            }
        )

        return stats


def main():
    """Command line interface for sync manager."""
    import os
    import sys

    # Get configuration from environment variables
    endpoint = os.getenv("PULSE_ENDPOINT", "")
    auth_token = os.getenv("PULSE_AUTH_TOKEN", "")

    sync_manager = SyncManager(endpoint=endpoint, auth_token=auth_token)

    if len(sys.argv) == 1 or "--help" in sys.argv:
        print("Sync Manager for Pulse")
        print("Usage: python sync_manager.py [command]")
        print("Commands:")
        print("  status    Show sync status")
        print("  sync      Sync all pending data")
        print("  force     Force sync all data (including already synced)")
        print("  recent    Sync only last 24 hours")
        print("\nEnvironment Variables:")
        print("  PULSE_ENDPOINT      Sync endpoint URL (required for sync)")
        print("  PULSE_AUTH_TOKEN    Bearer token for authentication")
        return

    command = sys.argv[1]

    if command == "status":
        status = sync_manager.get_sync_status()
        print("Sync Status:")
        print(f"  Device: {status['device']}")
        print(f"  Total hours available: {status['total_hours']}")
        print(f"  Already synced: {status['synced_hours']}")
        print(f"  Pending sync: {status['pending_hours']}")
        print(f"  Endpoint: {status['endpoint']}")
        if status["last_sync"]:
            print(f"  Last sync: {status['last_sync']}")

    elif command == "sync":
        results = sync_manager.sync_all()
        print(
            f"Sync completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )

    elif command == "force":
        results = sync_manager.sync_all(force=True)
        print(
            f"Force sync completed: {results['synced']} synced, "
            f"{results['failed']} failed"
        )

    elif command == "recent":
        results = sync_manager.sync_all(max_hours=24)
        print(
            f"Recent sync completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )

    else:
        print(f"Unknown command: {command}")
        print("Use --help for usage information")


if __name__ == "__main__":
    main()
