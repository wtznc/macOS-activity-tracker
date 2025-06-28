#!/bin/bash

# Build macOS App Bundle for Activity Tracker using PyInstaller

set -e

# Configuration
APP_NAME="Activity Tracker"
VERSION="${VERSION:-1.0.2}"  # Use environment variable if set, otherwise default
DIST_DIR="dist"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    if [[ "${CI:-false}" == "true" ]]; then
        echo "Running in CI environment, providing more details..."
        pwd
        ls -la
    fi
    exit 1
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Must run from project root directory"
fi

# Check if PyInstaller spec file exists
if [ ! -f "activity-tracker.spec" ]; then
    print_error "PyInstaller spec file not found: activity-tracker.spec"
fi

print_step "Building macOS App Bundle with PyInstaller..."

# Clean previous builds
print_step "Cleaning previous builds..."
rm -rf "$DIST_DIR"
rm -rf "build"

# Create and activate virtual environment for building
print_step "Setting up build environment..."
if [ ! -d "build_venv" ]; then
    python3 -m venv build_venv
fi

source build_venv/bin/activate

# Install build dependencies
print_step "Installing build dependencies..."
pip install --upgrade pip
pip install -e ".[build]"

# Verify PyInstaller installation
if ! command -v pyinstaller >/dev/null 2>&1; then
    print_error "PyInstaller not found in PATH"
fi

print_info "PyInstaller version: $(pyinstaller --version)"

# Build the app bundle
print_step "Building app bundle with PyInstaller..."
pyinstaller \
    --clean \
    --noconfirm \
    --log-level=INFO \
    activity-tracker.spec

# Verify the build
if [ ! -d "$DIST_DIR/$APP_NAME.app" ]; then
    print_error "App bundle was not created successfully"
fi

# Set proper permissions
print_step "Setting permissions..."
chmod -R 755 "$DIST_DIR/$APP_NAME.app"

# Verify the executable
EXECUTABLE_PATH="$DIST_DIR/$APP_NAME.app/Contents/MacOS/ActivityTracker"
if [ ! -f "$EXECUTABLE_PATH" ]; then
    print_error "Executable not found: $EXECUTABLE_PATH"
fi

if [ ! -x "$EXECUTABLE_PATH" ]; then
    print_error "Executable is not executable: $EXECUTABLE_PATH"
fi

print_step "App bundle created successfully!"
print_info "Location: $DIST_DIR/$APP_NAME.app"
print_info "Bundle size: $(du -sh "$DIST_DIR/$APP_NAME.app" | cut -f1)"
print_info "To install: Drag to Applications folder"

# Test the bundle quickly (without launching GUI)
print_step "Testing bundle integrity..."
if "$EXECUTABLE_PATH" --help >/dev/null 2>&1 || [ $? -eq 1 ]; then
    print_info "Bundle integrity check passed"
else
    print_error "Bundle integrity check failed"
fi

# Optional: Create DMG
if [[ "${CI:-false}" == "true" ]] || [[ "${CREATE_DMG:-}" == "true" ]]; then
    # In CI or when explicitly requested, create DMG automatically
    REPLY="y"
else
    read -p "Create installer DMG? (y/N): " -n 1 -r
    echo
fi

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Creating installer DMG..."
    DMG_NAME="ActivityTracker-$VERSION"

    # Create temporary directory for DMG contents
    DMG_DIR="$DIST_DIR/dmg_temp"
    mkdir -p "$DMG_DIR"

    # Copy app to DMG directory
    cp -R "$DIST_DIR/$APP_NAME.app" "$DMG_DIR/"

    # Create symlink to Applications
    ln -s /Applications "$DMG_DIR/Applications"

    # Create README for DMG
    cat > "$DMG_DIR/README.txt" << 'EOF'
Activity Tracker Installation
=============================

1. Drag "Activity Tracker.app" to the Applications folder
2. Launch Activity Tracker from Applications or Launchpad
3. Grant Accessibility permissions when prompted:
   - System Preferences > Security & Privacy > Privacy > Accessibility
   - Click the lock to make changes
   - Check "Activity Tracker"

For more help: https://github.com/wtznc/macOS-activity-tracker

Enjoy tracking your productivity!
EOF

    # Create DMG
    if command -v hdiutil >/dev/null 2>&1; then
        hdiutil create -volname "$DMG_NAME" -srcfolder "$DMG_DIR" -ov -format UDZO "$DIST_DIR/$DMG_NAME.dmg"

        if [ $? -eq 0 ]; then
            print_info "DMG created: $DIST_DIR/$DMG_NAME.dmg"
            print_info "DMG size: $(du -sh "$DIST_DIR/$DMG_NAME.dmg" | cut -f1)"
        else
            print_error "Failed to create DMG"
        fi
    else
        print_info "hdiutil not available, skipping DMG creation"
    fi

    # Clean up
    rm -rf "$DMG_DIR"
fi

print_step "Build complete!"
print_info "The app bundle is self-contained and includes all Python dependencies."
print_info "Users won't need to install Python or any packages separately."