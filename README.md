# macOS Activity Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.14+-green.svg)](https://www.apple.com/macos/)

A lightweight, privacy-focused macOS application that tracks your application usage and provides detailed insights into your digital productivity patterns.

## ✨ Features

- **🔍 Detailed Tracking**: Monitors active applications with window titles and file names
- **⚡ AFK Detection**: Automatically pauses tracking during idle periods
- **📊 Menu Bar Interface**: Native macOS menu bar app with intuitive controls
- **🚀 Performance Modes**: Fast mode (app names only) vs. detailed mode (full window titles)
- **🔄 Data Synchronization**: Built-in sync capabilities to remote endpoints
- **🛡️ Privacy First**: All data stays local unless explicitly synced

## 📦 Installation

### Quick Install (Recommended)

```bash
# Clone and run the all-in-one setup
git clone https://github.com/wtznc/macOS-activity-tracker.git
cd macOS-activity-tracker
./setup.sh all
```

This will:
- ✅ Install the Activity Tracker package
- ✅ Create a macOS app bundle
- ✅ Setup auto-start on login
- ✅ Launch the menu bar app

### Alternative Installation Options

```bash
# Just install the package
./setup.sh install

# Just create the app bundle
./setup.sh app

# Just setup auto-start
./setup.sh autostart

# Launch manually
./setup.sh launch
```

### Download Release

Download the latest release from [GitHub Releases](https://github.com/wtznc/macOS-activity-tracker/releases) and drag the app to your Applications folder.

## 🚀 Usage

### Menu Bar App

After installation, look for the Activity Tracker icon in your menu bar:

- ● **Green dot**: Tracking active
- ○ **Gray dot**: Tracking paused
- **Start/Stop**: Toggle tracking
- **Sync Data**: Upload data to remote endpoints
- **View Data**: Open data folder in Finder
- **Settings**: Configure verbose logging, fast mode, and AFK threshold

### Command Line

```bash
# Launch menu bar app
activity-tracker-menu

# Start tracking with console output
activity-tracker

# Fast mode (app names only, ~600x faster)
activity-tracker --fast

# Custom AFK threshold (default: 5 minutes)
activity-tracker --idle-threshold 120

# Check sync status
activity-tracker-sync status
```

## 📊 Data Storage

Activity data is stored locally in JSON format at:
```
~/Library/Application Support/ActivityTracker/data/
```

### Example Data Format

```json
{
  "Code - main.py — my-project": 45.2,
  "Safari - Documentation": 12.8,
  "iTerm2 - ~/projects": 2.0
}
```

## 🔄 Data Synchronization

```bash
# Check sync status
activity-tracker-sync status

# Sync all pending data
activity-tracker-sync sync

# View current device name
activity-tracker-sync status | grep Device
```

### Sync Data Format

Data is grouped by hour and includes device identification:

```json
{
  "timestamp": "2024-01-15T14:00:00Z",
  "device": "MacBook-Pro",
  "data": {
    "applications": {
      "Code - main.py — project": 1800.5,
      "Safari - Documentation": 1200.3
    },
    "total_time": 3600.8
  }
}
```

## ⚙️ Configuration

Configure via menu bar app settings or edit:
```
~/Library/Application Support/ActivityTracker/config/settings.json
```

```json
{
  "idle_threshold": 300,
  "fast_mode": false,
  "verbose_logging": true,
  "sync_endpoint": "https://your-server.com/api/activity"
}
```

## 🛡️ Privacy & Security

- **Local-first**: All data stored locally by default
- **No keylogging**: Only tracks active applications, not keystrokes
- **No screenshots**: Never captures screen content
- **Opt-in sync**: Data sharing only when explicitly configured
- **Open source**: Full transparency with source code available

## 📋 Requirements

- **macOS**: 10.14 (Mojave) or later
- **Python**: 3.9 or later
- **Permissions**: Accessibility access for window detection

## 🐛 Troubleshooting

### Permission Denied
Grant Accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility

### Installation Issues
```bash
# Reinstall pyobjc frameworks
pip3 install --upgrade pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

### Path Issues
```bash
# Add to your shell profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## 🔧 Development

```bash
# Setup development environment
git clone https://github.com/wtznc/macos-activity-tracker.git
cd macos-activity-tracker
make install-dev

# Run tests
make test

# Format code
make format
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ Star this repository if you find it useful!**
