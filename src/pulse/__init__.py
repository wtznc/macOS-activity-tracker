"""
Pulse - A lightweight application usage tracking tool.

This package provides comprehensive application and website usage tracking
for macOS systems with features including:

- Real-time application tracking with window title detection
- AFK (Away From Keyboard) detection
- Background operation via menu bar app
- Data synchronization capabilities
- JSON-based data storage
- VS Code integration with file-level tracking
"""

__version__ = "1.0.15"
__author__ = "Wojciech Tyziniec"
__license__ = "MIT"

from .core import Pulse
from .daemon import ActivityDaemon
from .sync import SyncManager

__all__ = [
    "Pulse",
    "SyncManager",
    "ActivityDaemon",
]
