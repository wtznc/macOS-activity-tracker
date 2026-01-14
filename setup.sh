#!/bin/bash

# macOS Activity Tracker - All-in-One Setup Script
# Handles installation, app creation, and auto-start configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  macOS Activity Tracker${NC}"
    echo -e "${BLUE}      Setup Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  install     Install the Activity Tracker package"
    echo "  app         Create macOS app bundle"
    echo "  autostart   Setup auto-start on login"
    echo "  launch      Launch the menu bar app"
    echo "  all         Do everything (install + app + autostart + launch)"
    echo
    echo "Examples:"
    echo "  $0 install      # Just install the package"
    echo "  $0 all          # Complete setup"
    echo "  $0 app          # Just create app bundle"
    echo
}

check_python() {
    print_step "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.9 or later."
    fi

    PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    REQUIRED_VERSION="3.9"

    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_error "Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or later is required."
    fi

    echo -e "${GREEN}[OK]${NC} Python $PYTHON_VERSION found"
}

install_package() {
    print_step "Installing Activity Tracker..."

    # Check if we're in a virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo "Virtual environment detected: $VIRTUAL_ENV"
        if [ -f "pyproject.toml" ]; then
            echo "Installing from local directory..."
            pip3 install -e .
        else
            echo "Installing from GitHub..."
            pip3 install git+https://github.com/wtznc/macOS-activity-tracker.git
        fi
    else
        # Create a virtual environment for installation
        echo "Creating virtual environment for installation..."
        python3 -m venv .venv
        source .venv/bin/activate

        if [ -f "pyproject.toml" ]; then
            echo "Installing from local directory..."
            pip3 install -e .
        else
            echo "Installing from GitHub..."
            pip3 install git+https://github.com/wtznc/macOS-activity-tracker.git
        fi

        # Create a wrapper script that activates the venv and runs the command
        INSTALL_DIR="$HOME/.local/bin"
        mkdir -p "$INSTALL_DIR"

        # Get the current directory
        CURRENT_DIR="$(pwd)"

        # Create wrapper scripts for each command
        for cmd in activity-tracker activity-tracker-menu activity-tracker-daemon activity-tracker-sync; do
            cat > "$INSTALL_DIR/$cmd" << EOF
#!/bin/bash
source "$CURRENT_DIR/.venv/bin/activate"
exec "$CURRENT_DIR/.venv/bin/$cmd" "\$@"
EOF
            chmod +x "$INSTALL_DIR/$cmd"
        done

        echo -e "${GREEN}[OK]${NC} Created wrapper scripts in $INSTALL_DIR"
    fi

    # Verify installation
    if command -v activity-tracker-menu &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Installation successful!"
    else
        print_error "Installation failed - CLI commands not found in PATH"
    fi
}

create_app() {
    print_step "Creating macOS App Bundle..."

    APP_NAME="Activity Tracker"
    APP_DIR="$APP_NAME.app"
    CONTENTS_DIR="$APP_DIR/Contents"
    MACOS_DIR="$CONTENTS_DIR/MacOS"
    RESOURCES_DIR="$CONTENTS_DIR/Resources"

    # Remove existing app if it exists
    if [ -d "$APP_DIR" ]; then
        rm -rf "$APP_DIR"
    fi

    # Create app bundle structure
    mkdir -p "$MACOS_DIR"
    mkdir -p "$RESOURCES_DIR"

    # Create Info.plist
    cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>ActivityTracker</string>
    <key>CFBundleIdentifier</key>
    <string>com.wtznc.activity-tracker</string>
    <key>CFBundleName</key>
    <string>Activity Tracker</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSBackgroundOnly</key>
    <false/>
</dict>
</plist>
EOF

    # Create the main executable script
    cat > "$MACOS_DIR/ActivityTracker" << EOF
#!/bin/bash
# Activity Tracker App Bundle Launcher

# Get the directory where this script is located
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="\$(dirname "\$(dirname "\$SCRIPT_DIR")")"

# Check if we have a local venv installation
if [ -f "\$PROJECT_DIR/.venv/bin/activity-tracker-menu" ]; then
    source "\$PROJECT_DIR/.venv/bin/activate"
    exec "\$PROJECT_DIR/.venv/bin/activity-tracker-menu"
elif command -v activity-tracker-menu &> /dev/null; then
    exec activity-tracker-menu
else
    osascript -e "display dialog \"Activity Tracker not installed. Please run: ./setup.sh install\" buttons {\"OK\"} default button \"OK\""
    exit 1
fi
EOF

    # Make the executable script runnable
    chmod +x "$MACOS_DIR/ActivityTracker"

    echo -e "${GREEN}[OK]${NC} App bundle created: $APP_DIR"
}

setup_autostart() {
    print_step "Setting up auto-start..."

    # Determine the command to use
    CURRENT_DIR="$(pwd)"
    if [ -f "$CURRENT_DIR/.venv/bin/activity-tracker-menu" ]; then
        COMMAND_PATH="$HOME/.local/bin/activity-tracker-menu"
    elif command -v activity-tracker-menu &> /dev/null; then
        COMMAND_PATH="$(which activity-tracker-menu)"
    else
        print_error "Activity Tracker not installed. Run 'install' first."
    fi

    PLIST_FILE="com.wtznc.activity-tracker.plist"
    LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_FILE"

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$LAUNCH_AGENTS_DIR"

    # Create the plist file dynamically
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wtznc.activity-tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>$COMMAND_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$CURRENT_DIR/activity_tracker.log</string>
    <key>StandardErrorPath</key>
    <string>$CURRENT_DIR/activity_tracker_error.log</string>
    <key>WorkingDirectory</key>
    <string>$CURRENT_DIR</string>
</dict>
</plist>
EOF

    # Load the LaunchAgent
    launchctl load "$PLIST_PATH" 2>/dev/null || true

    echo -e "${GREEN}[OK]${NC} Auto-start configured"
}

launch_app() {
    print_step "Launching Activity Tracker..."

    # Determine the command to use
    CURRENT_DIR="$(pwd)"
    if [ -f "$CURRENT_DIR/.venv/bin/activity-tracker-menu" ]; then
        COMMAND_PATH="$HOME/.local/bin/activity-tracker-menu"
    elif command -v activity-tracker-menu &> /dev/null; then
        COMMAND_PATH="activity-tracker-menu"
    else
        print_error "Activity Tracker not installed. Run 'install' first."
    fi

    # Launch in background
    nohup "$COMMAND_PATH" > /dev/null 2>&1 &
    APP_PID=$!

    echo -e "${GREEN}[OK]${NC} Activity Tracker started (PID: $APP_PID)"
    echo "[INFO] Look for the menu bar icon"
}

print_success() {
    echo
    echo -e "${GREEN}[SUCCESS] Setup Complete!${NC}"
    echo
    echo "[INFO] Usage:"
    echo "   activity-tracker-menu          # Launch menu bar app"
    echo "   activity-tracker --help        # Core tracker CLI"
    echo "   activity-tracker-sync status   # Check sync status"
    echo
    echo "[INFO] Data location: ~/Library/Application Support/ActivityTracker/"
    echo "[INFO] Full documentation: README.md"

    # Add PATH notice if needed
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo
        echo -e "${YELLOW}[WARN] NOTE:${NC} You may need to add ~/.local/bin to your PATH:"
        echo "   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
        echo "   source ~/.zshrc"
    fi
}

# Main script logic
print_header

if [ $# -eq 0 ]; then
    print_usage
    exit 1
fi

case "$1" in
    "install")
        check_python
        install_package
        print_success
        ;;
    "app")
        create_app
        echo -e "${GREEN}[OK]${NC} App bundle ready! Double-click 'Activity Tracker.app' to launch"
        ;;
    "autostart")
        setup_autostart
        echo -e "${GREEN}[OK]${NC} Auto-start enabled! Activity Tracker will start on login"
        ;;
    "launch")
        launch_app
        ;;
    "all")
        check_python
        install_package
        create_app
        setup_autostart
        launch_app
        print_success
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo
        print_usage
        exit 1
        ;;
esac
