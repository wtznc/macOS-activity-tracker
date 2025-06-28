#!/usr/bin/env python3
"""
Menu Bar Application for macOS Activity Tracker
Shows a menu bar icon when the tracker is running.
"""

import subprocess  # nosec B404 - Required for macOS Finder integration
import sys
import threading
from pathlib import Path

try:
    import objc
    from AppKit import (
        NSAlert,
        NSAlertStyleInformational,
        NSApplication,
        NSMenu,
        NSMenuItem,
        NSStatusBar,
        NSVariableStatusItemLength,
    )
    from Foundation import NSObject, NSTimer
except ImportError:
    print(
        "Error: pyobjc-framework-Cocoa not installed. "
        "Run: pip install pyobjc-framework-Cocoa"
    )
    exit(1)

try:
    from activity_tracker.core import ActivityTracker
    from activity_tracker.sync import SyncManager
    from activity_tracker.utils import get_data_directory
except ImportError:
    try:
        from .core import ActivityTracker
        from .sync import SyncManager
        from .utils import get_data_directory
    except ImportError:
        # If running as script, add parent directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        from core import ActivityTracker  # type: ignore[import,no-redef]
        from sync import SyncManager  # type: ignore[import,no-redef]
        from utils import get_data_directory  # type: ignore[import,no-redef]


class ActivityTrackerMenuBarDelegate(NSObject):
    def init(self):
        self = objc.super(ActivityTrackerMenuBarDelegate, self).init()
        if self is None:
            return None

        self.tracker = None
        self.tracker_thread = None
        self.is_running = False
        self.verbose_mode = True  # Enable verbose logging by default
        self.fast_mode = False
        self.idle_threshold = 300  # 5 minutes default
        self.sync_manager = SyncManager()

        # Create status bar item
        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(
            NSVariableStatusItemLength
        )

        # Set up the menu
        self.setup_menu()

        # Set initial icon
        self.update_icon()

        # Start timer to update status
        self.timer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                2.0, self, "updateStatus:", None, True
            )
        )

        return self

    def setup_menu(self):
        """Set up the menu bar menu."""
        self.menu = NSMenu.alloc().init()

        # Status item
        self.status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Status: Stopped", None, ""
        )
        self.menu.addItem_(self.status_menu_item)

        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # Start/Stop item
        self.toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Start Tracking", "toggleTracking:", ""
        )
        self.toggle_item.setTarget_(self)
        self.menu.addItem_(self.toggle_item)

        # View Data item
        data_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "View Data Folder", "openDataFolder:", ""
        )
        data_item.setTarget_(self)
        self.menu.addItem_(data_item)

        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # Sync Data item
        sync_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Sync Data", "syncData:", ""
        )
        sync_item.setTarget_(self)
        self.menu.addItem_(sync_item)

        # Sync Status item
        sync_status_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Sync Status", "showSyncStatus:", ""
        )
        sync_status_item.setTarget_(self)
        self.menu.addItem_(sync_status_item)

        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # Verbose Mode toggle
        self.verbose_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Enable Verbose Logging", "toggleVerbose:", ""
        )
        self.verbose_item.setTarget_(self)
        self.menu.addItem_(self.verbose_item)

        # Fast Mode toggle
        self.fast_mode_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Enable Fast Mode", "toggleFastMode:", ""
        )
        self.fast_mode_item.setTarget_(self)
        self.menu.addItem_(self.fast_mode_item)

        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # Quit item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quitApp:", ""
        )
        quit_item.setTarget_(self)
        self.menu.addItem_(quit_item)

        # Set the menu
        self.status_item.setMenu_(self.menu)

    def update_icon(self):
        """Update the menu bar icon based on tracking status."""
        button = self.status_item.button()
        if self.is_running:
            button.setTitle_("●")  # Filled circle for running
        else:
            button.setTitle_("○")  # Empty circle for stopped

    @objc.IBAction
    def updateStatus_(self, timer):
        """Update the status display."""
        if self.is_running:
            self.status_menu_item.setTitle_("Status: Running")
            self.toggle_item.setTitle_("Stop Tracking")
        else:
            self.status_menu_item.setTitle_("Status: Stopped")
            self.toggle_item.setTitle_("Start Tracking")

        # Update verbose menu item
        if self.verbose_mode:
            self.verbose_item.setTitle_("Disable Verbose Logging")
        else:
            self.verbose_item.setTitle_("Enable Verbose Logging")

        # Update fast mode menu item
        if self.fast_mode:
            self.fast_mode_item.setTitle_("Disable Fast Mode")
        else:
            self.fast_mode_item.setTitle_("Enable Fast Mode")

        self.update_icon()

    @objc.IBAction
    def toggleTracking_(self, sender):
        """Toggle tracking on/off."""
        print(f"Toggle tracking called, is_running: {self.is_running}")
        if self.is_running:
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        """Start the activity tracker."""
        if not self.is_running:
            self.tracker = ActivityTracker(
                verbose=self.verbose_mode,
                fast_mode=self.fast_mode,
                include_window_titles=not self.fast_mode,
                idle_threshold=self.idle_threshold,
            )
            self.tracker_thread = threading.Thread(
                target=self.tracker.start, daemon=True
            )
            self.tracker_thread.start()
            self.is_running = True

            mode_desc = ""
            if self.fast_mode:
                mode_desc = " (fast mode - app names only)"
            elif self.verbose_mode:
                mode_desc = " (verbose logging with window titles)"

            print(f"Activity tracking started{mode_desc}")

    def stop_tracking(self):
        """Stop the activity tracker."""
        if self.is_running and self.tracker:
            self.tracker.stop()
            self.is_running = False
            print("Activity tracking stopped")

    @objc.IBAction
    def toggleVerbose_(self, sender):
        """Toggle verbose logging mode."""
        self.verbose_mode = not self.verbose_mode
        print(f"Verbose logging {'enabled' if self.verbose_mode else 'disabled'}")

        # Restart tracking with new verbose setting if currently running
        if self.is_running:
            print("Restarting tracker with new verbose setting...")
            self.stop_tracking()
            # Small delay to ensure clean shutdown
            import time

            time.sleep(0.5)
            self.start_tracking()

    @objc.IBAction
    def toggleFastMode_(self, sender):
        """Toggle fast mode (app names only, no window titles)."""
        self.fast_mode = not self.fast_mode
        mode_name = (
            "fast mode (app names only)"
            if self.fast_mode
            else "detailed mode (app + window titles)"
        )
        print(f"Switched to {mode_name}")

        # Fast mode overrides verbose for performance
        if self.fast_mode and self.verbose_mode:
            print("Note: Fast mode reduces detection time from ~140ms to <1ms")

        # Restart tracking with new mode if currently running
        if self.is_running:
            print("Restarting tracker with new mode...")
            self.stop_tracking()
            import time

            time.sleep(0.5)
            self.start_tracking()

    @objc.IBAction
    def syncData_(self, sender):
        """Sync activity data to remote endpoint."""
        # Show starting alert
        start_alert = NSAlert.alloc().init()
        start_alert.setAlertStyle_(NSAlertStyleInformational)
        start_alert.setMessageText_("Starting Sync")
        start_alert.setInformativeText_(
            "Syncing activity data to remote endpoint...\n\n"
            "This may take a few moments."
        )
        start_alert.addButtonWithTitle_("OK")
        start_alert.runModal()

        try:
            # Run sync synchronously for simplicity
            results = self.sync_manager.sync_all()

            # Show completion alert
            alert = NSAlert.alloc().init()
            alert.setAlertStyle_(NSAlertStyleInformational)
            alert.setMessageText_("Sync Completed")

            if results["failed"] > 0:
                alert_text = (
                    f"⚠️ {results['failed']} hours failed to sync.\n"
                    f"Check network connection.\n\n"
                    f"Synced: {results['synced']}\nSkipped: {results['skipped']}"
                )
            elif results["synced"] > 0:
                alert_text = (
                    f"✓ Successfully synced {results['synced']} hours of data\n\n"
                    f"Skipped: {results['skipped']} (already synced)"
                )
            else:
                alert_text = "ℹ️ All data already synced\n\nNo new data to upload"

            alert.setInformativeText_(alert_text)
            alert.addButtonWithTitle_("OK")
            alert.runModal()

            # Also print to terminal for debugging
            print(
                f"Sync completed: {results['synced']} synced, "
                f"{results['failed']} failed, {results['skipped']} skipped"
            )

        except Exception as e:
            # Show error alert
            error_alert = NSAlert.alloc().init()
            error_alert.setAlertStyle_(NSAlertStyleInformational)
            error_alert.setMessageText_("Sync Error")
            error_alert.setInformativeText_(f"Error during sync: \n\n{str(e)}")
            error_alert.addButtonWithTitle_("OK")
            error_alert.runModal()

            print(f"✗ Sync error: {e}")

    @objc.IBAction
    def showSyncStatus_(self, sender):
        """Show current sync status in a macOS alert window."""
        try:
            status = self.sync_manager.get_sync_status()

            # Create alert window
            alert = NSAlert.alloc().init()
            alert.setAlertStyle_(NSAlertStyleInformational)
            alert.setMessageText_("Activity Tracker - Sync Status")

            # Format status information
            status_text = f"""Total hours available: {status['total_hours']}
Already synced: {status['synced_hours']}
Pending sync: {status['pending_hours']}

Endpoint: {status['endpoint']}

Last sync: {status['last_sync'] if status['last_sync'] else 'Never'}"""

            alert.setInformativeText_(status_text)
            alert.addButtonWithTitle_("OK")

            # Show the alert
            alert.runModal()

        except Exception as e:
            # Show error in alert window
            error_alert = NSAlert.alloc().init()
            error_alert.setAlertStyle_(NSAlertStyleInformational)
            error_alert.setMessageText_("Sync Status Error")
            error_alert.setInformativeText_(f"Error getting sync status: {e}")
            error_alert.addButtonWithTitle_("OK")
            error_alert.runModal()

    @objc.IBAction
    def openDataFolder_(self, sender):
        """Open the data folder in Finder."""
        data_path = get_data_directory()
        subprocess.run(
            ["open", str(data_path)], check=False
        )  # nosec B603,B607 - Safe macOS open command

    @objc.IBAction
    def quitApp_(self, sender):
        """Quit the application."""
        if self.is_running:
            self.stop_tracking()
        NSApplication.sharedApplication().terminate_(None)


class MenuBarApp:
    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.delegate = ActivityTrackerMenuBarDelegate.alloc().init()

        # Set up the app
        self.app.setActivationPolicy_(2)  # NSApplicationActivationPolicyAccessory

    def run(self):
        """Run the menu bar application."""
        print("Starting menu bar app...")
        print("Look for the activity tracker icon in your menu bar")

        try:
            self.app.run()
        except KeyboardInterrupt:
            print("\nShutting down...")
            if self.delegate.is_running:
                self.delegate.stop_tracking()


def main():
    """Main entry point."""
    import sys

    # Prevent running multiple instances
    try:
        app = MenuBarApp()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user. Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
