#!/usr/bin/env python3
"""
HTTP synchronization client for Activity Tracker.
Handles all HTTP communication with remote endpoints.
"""

import platform
import socket
from datetime import datetime
from typing import Dict

import requests


class DeviceIdentifier:
    """Generates device identification information."""

    @staticmethod
    def get_device_name() -> str:
        """Get the device/laptop name for identification."""
        try:
            hostname = socket.gethostname()

            # On macOS, remove .local suffix
            if hostname.endswith(".local"):
                hostname = hostname[:-6]

            # If hostname is generic, fall back to platform node
            if not hostname or hostname in ["localhost", "unknown"]:
                hostname = platform.node()
                if hostname.endswith(".local"):
                    hostname = hostname[:-6]

            return hostname
        except Exception:
            return f"macos-{platform.machine()}"


class SyncPayloadBuilder:
    """Builds payloads for sync endpoints."""

    def __init__(self):
        self.device_identifier = DeviceIdentifier()

    def create_sync_payload(self, hour_key: str, hour_data: Dict) -> Dict:
        """Create payload for sync endpoint."""
        dt = datetime.strptime(hour_key, "%Y-%m-%d_%H")

        return {
            "timestamp": dt.isoformat(),
            "hour": hour_key,
            "data": hour_data,
            "source": "macos-activity-tracker",
            "device": self.device_identifier.get_device_name(),
            "version": "1.0",
        }


class HttpSyncClient:
    """HTTP client for syncing data to remote endpoints."""

    def __init__(self, endpoint: str, auth_token: str = ""):
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.payload_builder = SyncPayloadBuilder()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication if configured."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def sync_hour_data(self, hour_key: str, hour_data: Dict) -> bool:
        """Sync single hour of data to endpoint."""
        payload = self.payload_builder.create_sync_payload(hour_key, hour_data)

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )

            if response.status_code in [200, 201]:
                print(
                    f"[OK] Synced {hour_key}: {hour_data['total_time']: .1f}s across "
                    f"{hour_data['files_processed']} files"
                )
                return True
            else:
                print(
                    f"[FAIL] Sync failed for {hour_key}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            print(f"[FAIL] Network error syncing {hour_key}: {e}")
            return False
        except Exception as e:
            print(f"[FAIL] Error syncing {hour_key}: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to the sync endpoint."""
        try:
            # Simple GET request to test connectivity
            response = requests.get(self.endpoint, timeout=10)
            return response.status_code < 500
        except Exception:
            return False


class SyncResultCollector:
    """Collects and manages sync operation results."""

    def __init__(self):
        self.results = {"synced": 0, "failed": 0, "skipped": 0}

    def record_sync_success(self):
        """Record a successful sync."""
        self.results["synced"] += 1

    def record_sync_failure(self):
        """Record a failed sync."""
        self.results["failed"] += 1

    def record_sync_skip(self):
        """Record a skipped sync."""
        self.results["skipped"] += 1

    def get_results(self) -> Dict[str, int]:
        """Get sync results."""
        return self.results.copy()

    def print_summary(self):
        """Print sync summary."""
        print(
            f"Sync completed: {self.results['synced']} synced, "
            f"{self.results['failed']} failed, {self.results['skipped']} skipped"
        )
