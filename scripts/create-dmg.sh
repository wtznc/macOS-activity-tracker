#!/bin/bash

# Create DMG installer for Activity Tracker

set -e

# Configuration
APP_NAME="Activity Tracker"
VERSION="1.0.0"
DIST_DIR="dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"
DMG_NAME="ActivityTracker-$VERSION"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[DMG]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if app bundle exists
if [ ! -d "$APP_DIR" ]; then
    print_error "App bundle not found. Run ./scripts/build-app.sh first."
fi

print_step "Creating DMG installer..."

# Create temporary directory for DMG contents
DMG_DIR="$DIST_DIR/dmg_temp"
rm -rf "$DMG_DIR"
mkdir -p "$DMG_DIR"

# Copy app bundle
print_step "Copying app bundle..."
cp -R "$APP_DIR" "$DMG_DIR/"

# Create Applications symlink
print_step "Creating Applications symlink..."
ln -s /Applications "$DMG_DIR/Applications"

# Create README for DMG
print_step "Creating installation instructions..."
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

# Set DMG background and layout (optional)
mkdir -p "$DMG_DIR/.background"

# Create DMG
print_step "Creating DMG file..."
hdiutil create -volname "$DMG_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "$DIST_DIR/$DMG_NAME.dmg"

# Clean up temporary directory
rm -rf "$DMG_DIR"

print_step "DMG created successfully!"
print_info "File: $DIST_DIR/$DMG_NAME.dmg"
print_info "Size: $(du -h "$DIST_DIR/$DMG_NAME.dmg" | cut -f1)"