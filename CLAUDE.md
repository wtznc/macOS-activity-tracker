# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Preferences

- Never include Co-Authored-By or any Claude signature in commit messages or PR descriptions
- Never use emojis anywhere; remove emojis when encountered

## Build and Development Commands

```bash
# Install for development (includes dev dependencies + pre-commit hooks)
make install-dev

# Run from source
python -m pulse.menu_bar

# Build macOS app bundle
make install-build  # Install PyInstaller first
make app            # Creates dist/Pulse.app

# Run tests
make test                    # Run all tests
make test-cov                # Run tests with coverage report
pytest tests/test_core.py    # Run single test file
pytest -k "test_name"        # Run specific test by name

# Code quality
make lint     # Run flake8, mypy, black --check, isort --check
make format   # Auto-format with black and isort

# Clean build artifacts
make clean
```

## Architecture

This is a macOS menu bar application that tracks application usage time. The codebase follows a composition-based architecture with single-responsibility classes.

### Core Components (src/pulse/)

**Entry Points:**
- `menu_bar.py` - Native macOS menu bar app using PyObjC (main user-facing interface)
- `core.py` - CLI entry point and `Pulse` class that orchestrates tracking
- `daemon.py` - Background daemon mode
- `sync.py` - CLI for data synchronization

**Detection Layer (`detection.py`):**
- `ApplicationDetector` - Gets active app via NSWorkspace
- `WindowTitleDetector` - Gets window titles via AppleScript or Quartz framework
- `IdleDetector` - Detects AFK state using CGEventSource
- `TitleCleaner` - Normalizes window titles and handles Unicode

**Monitoring Layer (`activity_monitor.py`):**
- `ActivityMonitor` - Coordinates detection with debouncing logic
- `ActivityLogger` - Handles verbose console output

**Storage Layer (`storage.py`):**
- `ActivityDataStore` - Persists per-minute JSON files to ~/Library/Application Support/Pulse/
- `SessionTracker` - Tracks in-memory session data

**Sync Layer:**
- `sync.py` - `SyncManager` orchestrates sync operations
- `data_aggregator.py` - Groups minute files into hourly aggregates
- `http_sync.py` - HTTP client for remote sync

### Data Flow

1. `ActivityMonitor` polls active app every 500ms with debouncing
2. App switches and durations are recorded in `SessionTracker`
3. Every minute boundary, data is saved via `ActivityDataStore` as JSON files
4. Files are named `activity_YYYYMMDD_HHMM.json` containing `{app_name: seconds}` pairs
5. `SyncManager` can aggregate and upload hourly data to a remote endpoint

### macOS Integration

Uses PyObjC for native macOS APIs:
- AppKit: Menu bar status item, alerts, NSWorkspace
- Quartz: Window list enumeration, idle time detection
- AppleScript (via subprocess): Window titles for specific apps

### Key Design Patterns

- **Composition over inheritance**: Core classes inject specialized components
- **Debouncing**: App switches require stable detection for 0.3-1.0s before recording
- **Minute-bounded time**: Data is saved per-minute with time properly attributed across boundaries
- **Idle handling**: Tracking pauses after configurable threshold (default 5 min)
