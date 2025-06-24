#!/bin/bash

# Build macOS App Bundle for Activity Tracker

set -e

# Configuration
APP_NAME="Activity Tracker"
BUNDLE_ID="com.wtznc.activity-tracker"
VERSION="${VERSION:-1.0.0}"  # Use environment variable if set, otherwise default
DIST_DIR="dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"

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

print_step "Building macOS App Bundle..."

# Create distribution directory
mkdir -p "$DIST_DIR"
rm -rf "$APP_DIR"

# Create app bundle structure
print_step "Creating app bundle structure..."
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"
mkdir -p "$APP_DIR/Contents/Frameworks"

# Copy Python environment
print_step "Copying Python environment..."
if [ -d "venv" ]; then
    cp -R venv "$APP_DIR/Contents/Frameworks/"
    # Clean up cache files
    find "$APP_DIR/Contents/Frameworks/venv" -name "*.pyc" -delete
    find "$APP_DIR/Contents/Frameworks/venv" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
fi

# Copy source code
print_step "Copying source code..."
cp -R src "$APP_DIR/Contents/Resources/"

# Create Info.plist
print_step "Creating Info.plist..."
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>ActivityTracker</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2025 Wojciech Tyziniec. MIT License.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>Activity Tracker needs to access application information to track your usage.</string>
    <key>NSSystemAdministrationUsageDescription</key>
    <string>Activity Tracker needs system access to monitor application usage.</string>
</dict>
</plist>
EOF

# Create executable script
print_step "Creating executable..."
cat > "$APP_DIR/Contents/MacOS/ActivityTracker" << 'EOF'
#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
RESOURCES_DIR="$APP_DIR/Resources"
FRAMEWORKS_DIR="$APP_DIR/Frameworks"

# Set up Python environment
export PYTHONPATH="$RESOURCES_DIR/src:$PYTHONPATH"

# Use bundled Python if available, otherwise system Python
if [ -d "$FRAMEWORKS_DIR/venv" ]; then
    PYTHON="$FRAMEWORKS_DIR/venv/bin/python"
else
    PYTHON="python3"
fi

# Change to resources directory
cd "$RESOURCES_DIR"

# Launch the menu bar app directly without using -m to avoid import conflicts
exec "$PYTHON" "$RESOURCES_DIR/src/activity_tracker/menu_bar.py"
EOF

chmod +x "$APP_DIR/Contents/MacOS/ActivityTracker"

# Create PkgInfo
echo -n "APPL????" > "$APP_DIR/Contents/PkgInfo"

# Set proper permissions
print_step "Setting permissions..."
chmod -R 755 "$APP_DIR"

# Create app icon (basic text-based icon for now)
print_step "Creating app icon..."
mkdir -p "$APP_DIR/Contents/Resources/AppIcon.iconset"
# For now, just create an empty icon file to prevent errors
touch "$APP_DIR/Contents/Resources/AppIcon.iconset/icon_512x512.png" || true

print_step "App bundle created successfully!"
print_info "Location: $APP_DIR"
print_info "To install: Drag to Applications folder"

# Optional: Create a simple installer
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
    cp -R "$APP_DIR" "$DMG_DIR/"

    # Create symlink to Applications
    ln -s /Applications "$DMG_DIR/Applications"

    # Create DMG
    if command -v hdiutil >/dev/null 2>&1; then
        hdiutil create -volname "$DMG_NAME" -srcfolder "$DMG_DIR" -ov -format UDZO "$DIST_DIR/$DMG_NAME.dmg"

        if [ $? -eq 0 ]; then
            print_info "DMG created: $DIST_DIR/$DMG_NAME.dmg"
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
