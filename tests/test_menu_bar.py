"""Tests for menu bar application."""

import sys
import unittest
from unittest.mock import MagicMock, patch

# Need to patch imports BEFORE importing menu_bar

# Define a mock NSObject class that supports alloc().init() pattern
class MockNSObject:
    @classmethod
    def alloc(cls):
        return cls()
    
    def init(self):
        return self

    def initWithTitle_action_keyEquivalent_(self, title, action, key):
        self.title = title
        return self

# Mock AppKit/Foundation/objc modules
mock_objc = MagicMock()
# Mock objc.super to return an object that responds to init()
# When super(Class, self).init() is called, it returns self (simplified)
def mock_super(cls, self_obj):
    # Return a mock object that simulates the superclass
    # Its init() method should return the original self_obj
    super_mock = MagicMock()
    super_mock.init.return_value = self_obj
    return super_mock

mock_objc.super = mock_super

# Configure objc decorators to be identity functions
def identity(func):
    return func
mock_objc.IBAction = identity
mock_objc.python_method = identity

sys.modules["objc"] = mock_objc
sys.modules["AppKit"] = MagicMock()
# Assign our MockNSObject
sys.modules["Foundation"] = MagicMock()
sys.modules["Foundation"].NSObject = MockNSObject

# Now we can safely import the module under test
from activity_tracker.menu_bar import ActivityTrackerMenuBarDelegate, MenuBarApp, main


class TestActivityTrackerMenuBarDelegate(unittest.TestCase):
    """Test cases for ActivityTrackerMenuBarDelegate."""

    def setUp(self):
        """Set up test fixtures."""
        # Since we are using a real class inheriting from MockNSObject, 
        # alloc().init() works and calls our actual init method.
        # But we need to ensure other dependencies (NSStatusBar, etc.) are mocked correctly.
        
        # Patching inside setUp is safer for method-level isolation, but we need
        # the class properly initialized.
        
        # We need to mock NSStatusBar.systemStatusBar()
        self.mock_status_bar = MagicMock()
        sys.modules["AppKit"].NSStatusBar.systemStatusBar.return_value = self.mock_status_bar
        
        # Create delegate
        self.delegate = ActivityTrackerMenuBarDelegate.alloc().init()
        
        # Reset mocks/attributes for clean state if needed
        # Since init() ran, these attributes are set from the code.
        # We might need to replace them with fresh mocks if we want to assert calls
        # made *during test*, not during init.
        
        # Mock items for testing actions
        self.delegate.status_item = MagicMock()
        self.delegate.status_menu_item = MagicMock()
        self.delegate.toggle_item = MagicMock()
        self.delegate.verbose_item = MagicMock()
        self.delegate.fast_mode_item = MagicMock()
        self.delegate.tracker = MagicMock()
        self.delegate.sync_manager = MagicMock()

    def test_init(self):
        """Test initialization."""
        self.assertIsNotNone(self.delegate)
        # We can't easily assert is_running because our MockNSObject doesn't fully simulate
        # the super().init() chain if it relied on other things, but here it's fine.
        # The code sets self.is_running = False
        self.assertFalse(self.delegate.is_running)
        self.assertTrue(self.delegate.verbose_mode)
        # self.delegate.status_item was mocked in setUp, but in init it was set from NSStatusBar
        # We verify init logic:
        sys.modules["AppKit"].NSStatusBar.systemStatusBar.assert_called()

    def test_update_icon_running(self):
        """Test icon update when running."""
        self.delegate.is_running = True
        self.delegate.update_icon()
        self.delegate.status_item.button().setTitle_.assert_called_with("●")

    def test_update_icon_stopped(self):
        """Test icon update when stopped."""
        self.delegate.is_running = False
        self.delegate.update_icon()
        self.delegate.status_item.button().setTitle_.assert_called_with("○")

    def test_update_status_running(self):
        """Test update status when running."""
        self.delegate.is_running = True
        self.delegate.verbose_mode = True
        self.delegate.fast_mode = False
        
        self.delegate.updateStatus_(None)
        
        self.delegate.status_menu_item.setTitle_.assert_called_with("Status: Running")
        self.delegate.toggle_item.setTitle_.assert_called_with("Stop Tracking")
        self.delegate.verbose_item.setTitle_.assert_called_with("Disable Verbose Logging")
        self.delegate.fast_mode_item.setTitle_.assert_called_with("Enable Fast Mode")

    def test_update_status_stopped(self):
        """Test update status when stopped."""
        self.delegate.is_running = False
        self.delegate.verbose_mode = False
        self.delegate.fast_mode = True
        
        self.delegate.updateStatus_(None)
        
        self.delegate.status_menu_item.setTitle_.assert_called_with("Status: Stopped")
        self.delegate.toggle_item.setTitle_.assert_called_with("Start Tracking")
        self.delegate.verbose_item.setTitle_.assert_called_with("Enable Verbose Logging")
        self.delegate.fast_mode_item.setTitle_.assert_called_with("Disable Fast Mode")

    def test_toggle_tracking(self):
        """Test toggle tracking action."""
        # Start
        with patch("activity_tracker.menu_bar.ActivityTracker") as mock_tracker:
            with patch("threading.Thread") as mock_thread:
                self.delegate.toggleTracking_(None)
        
        self.assertTrue(self.delegate.is_running)
        
        # Stop
        self.delegate.toggleTracking_(None)
        self.assertFalse(self.delegate.is_running)

    def test_start_tracking_already_running(self):
        """Test start tracking when already running."""
        self.delegate.is_running = True
        with patch("builtins.print") as mock_print:
            self.delegate.start_tracking()
        
        # Should do nothing
        mock_print.assert_not_called()

    def test_stop_tracking_not_running(self):
        """Test stop tracking when not running."""
        self.delegate.is_running = False
        with patch("builtins.print") as mock_print:
            self.delegate.stop_tracking()
            
        mock_print.assert_not_called()

    @patch("time.sleep")
    def test_toggle_verbose(self, mock_sleep):
        """Test toggle verbose mode."""
        # Toggle on -> off
        self.delegate.verbose_mode = True
        self.delegate.is_running = True
        self.delegate.tracker = MagicMock()
        old_tracker = self.delegate.tracker
        
        with patch("activity_tracker.menu_bar.ActivityTracker") as mock_tracker_cls:
             with patch("threading.Thread"):
                self.delegate.toggleVerbose_(None)
        
        self.assertFalse(self.delegate.verbose_mode)
        # Should restart tracker
        old_tracker.stop.assert_called()
        mock_tracker_cls.assert_called() # New tracker created

    @patch("time.sleep")
    def test_toggle_fast_mode(self, mock_sleep):
        """Test toggle fast mode."""
        self.delegate.fast_mode = False
        self.delegate.is_running = True
        self.delegate.tracker = MagicMock()
        old_tracker = self.delegate.tracker

        with patch("activity_tracker.menu_bar.ActivityTracker") as mock_tracker_cls:
             with patch("threading.Thread"):
                self.delegate.toggleFastMode_(None)
                
        self.assertTrue(self.delegate.fast_mode)
        old_tracker.stop.assert_called()

    @patch("activity_tracker.menu_bar.subprocess.run")
    def test_open_data_folder(self, mock_run):
        """Test open data folder."""
        self.delegate.openDataFolder_(None)
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "/usr/bin/open")

    def test_quit_app(self):
        """Test quit app."""
        self.delegate.is_running = True
        self.delegate.tracker = MagicMock()
        
        with patch("AppKit.NSApplication") as mock_app:
            self.delegate.quitApp_(None)
            
        self.delegate.tracker.stop.assert_called()
        # terminate_ called on sharedApplication
        # NSApplication.sharedApplication().terminate_(None)

    @patch("activity_tracker.menu_bar.NSAlert")
    def test_sync_data_success(self, mock_alert_cls):
        """Test sync data success."""
        # Use our MockNSObject logic or MagicMock for NSAlert
        mock_alert = MagicMock()
        mock_alert_cls.alloc.return_value.init.return_value = mock_alert
        
        self.delegate.sync_manager.sync_all.return_value = {"synced": 5, "failed": 0, "skipped": 0}
        
        self.delegate.syncData_(None)
        
        self.delegate.sync_manager.sync_all.assert_called()
        # Verify success message
        # We can't easily inspect setInformativeText_ argument string content exactly 
        # without complex matching, but we verify it ran modal
        mock_alert.runModal.assert_called()

    @patch("activity_tracker.menu_bar.NSAlert")
    def test_sync_data_failure(self, mock_alert_cls):
        """Test sync data with failures."""
        mock_alert = MagicMock()
        mock_alert_cls.alloc.return_value.init.return_value = mock_alert
        self.delegate.sync_manager.sync_all.return_value = {"synced": 0, "failed": 5, "skipped": 0}
        
        self.delegate.syncData_(None)
        mock_alert.runModal.assert_called()

    @patch("activity_tracker.menu_bar.NSAlert")
    def test_sync_data_exception(self, mock_alert_cls):
        """Test sync data exception handling."""
        mock_alert = MagicMock()
        mock_alert_cls.alloc.return_value.init.return_value = mock_alert
        self.delegate.sync_manager.sync_all.side_effect = Exception("Sync failed")
        
        self.delegate.syncData_(None)
        mock_alert.runModal.assert_called()

    @patch("activity_tracker.menu_bar.NSAlert")
    def test_show_sync_status(self, mock_alert_cls):
        """Test show sync status."""
        mock_alert = MagicMock()
        mock_alert_cls.alloc.return_value.init.return_value = mock_alert
        self.delegate.sync_manager.get_sync_status.return_value = {
            "total_hours": 10,
            "synced_hours": 5,
            "pending_hours": 5,
            "endpoint": "http://test",
            "last_sync": "Today"
        }
        
        self.delegate.showSyncStatus_(None)
        mock_alert.runModal.assert_called()

    @patch("activity_tracker.menu_bar.NSAlert")
    def test_show_sync_status_error(self, mock_alert_cls):
        """Test show sync status error."""
        self.delegate.sync_manager.get_sync_status.side_effect = Exception("Error")
        self.delegate.showSyncStatus_(None)
        mock_alert_cls.alloc.return_value.init.return_value.runModal.assert_called()


class TestMenuBarApp(unittest.TestCase):
    """Test cases for MenuBarApp class."""
    
    @patch("activity_tracker.menu_bar.ActivityTrackerMenuBarDelegate")
    def test_run(self, mock_delegate_cls):
        """Test app run."""
        app = MenuBarApp()
        with patch("builtins.print"):
             app.run()
        
        app.app.run.assert_called()

    @patch("activity_tracker.menu_bar.ActivityTrackerMenuBarDelegate")
    def test_run_interrupt(self, mock_delegate_cls):
        """Test app run interrupt."""
        app = MenuBarApp()
        app.app.run.side_effect = KeyboardInterrupt
        
        # Mock delegate instance
        mock_delegate_instance = mock_delegate_cls.alloc().init()
        mock_delegate_instance.is_running = True
        app.delegate = mock_delegate_instance
        
        with patch("builtins.print"):
             app.run()
        
        mock_delegate_instance.stop_tracking.assert_called()


class TestMain(unittest.TestCase):
    """Test main function."""
    
    @patch("activity_tracker.menu_bar.MenuBarApp")
    def test_main(self, mock_app_cls):
        """Test main."""
        main()
        mock_app_cls.return_value.run.assert_called()

    @patch("activity_tracker.menu_bar.MenuBarApp")
    def test_main_interrupt(self, mock_app_cls):
        """Test main interrupt."""
        mock_app_cls.return_value.run.side_effect = KeyboardInterrupt
        with self.assertRaises(SystemExit):
            with patch("builtins.print"):
                main()

    @patch("activity_tracker.menu_bar.MenuBarApp")
    def test_main_error(self, mock_app_cls):
        """Test main error."""
        mock_app_cls.side_effect = Exception("Setup failed")
        with self.assertRaises(SystemExit):
            with patch("builtins.print"):
                main()

if __name__ == "__main__":
    unittest.main()
