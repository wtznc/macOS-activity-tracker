"""Pytest configuration and fixtures."""

import shutil
import tempfile

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_activity_data():
    """Sample activity data for testing."""
    return {
        "Code - main.py — my-project": 45.2,
        "Safari - GitHub": 12.8,
        "iTerm2 - ~/projects": 2.0,
    }


@pytest.fixture
def sample_hour_data():
    """Sample hourly aggregated data for testing."""
    return {
        "timestamp": "2024-01-15T14:00:00Z",
        "hour": "2024-01-15_14",
        "data": {
            "applications": {
                "Code - main.py — my-project": 1800.5,
                "Safari - GitHub": 1200.3,
                "iTerm2 - ~/projects": 599.2,
            },
            "total_time": 3600.0,
            "files_processed": 60,
        },
        "source": "macos-activity-tracker",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_macos_apps():
    """Mock macOS application data."""
    return [
        {
            "name": "Visual Studio Code",
            "bundle_id": "com.microsoft.VSCode",
            "window_title": "main.py — my-project",
        },
        {
            "name": "Safari",
            "bundle_id": "com.apple.Safari",
            "window_title": "GitHub - Activity Tracker",
        },
        {
            "name": "iTerm2",
            "bundle_id": "com.googlecode.iterm2",
            "window_title": "Terminal — ~/projects",
        },
    ]


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")
