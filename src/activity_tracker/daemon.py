#!/usr/bin/env python3
"""
Daemon wrapper for the activity tracker.
Handles running the tracker as a background service.
"""

import fcntl
import os
import signal

# subprocess not needed - using os.fork() and os.kill() instead
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from .core import ActivityTracker


class ActivityDaemon:
    def __init__(self, pidfile: Optional[str] = None):
        if pidfile is None:
            # Use secure temporary directory
            temp_dir = Path(tempfile.gettempdir())
            self.pidfile = str(temp_dir / "activity_tracker.pid")
        else:
            self.pidfile = pidfile
        self.tracker: Optional[ActivityTracker] = None

    def daemonize(self):
        """Daemonize the process."""
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit parent
        except OSError as e:
            sys.stderr.write(f"Fork #1 failed: {e}\n")
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0o077)  # Restrictive umask: owner read/write only

        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit second parent
        except OSError as e:
            sys.stderr.write(f"Fork #2 failed: {e}\n")
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Write pidfile with exclusive lock to prevent race conditions
        try:
            with open(self.pidfile, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                f.write(str(os.getpid()))
                f.flush()
        except BlockingIOError:
            sys.stderr.write("Another daemon instance is already starting\n")
            sys.exit(1)

    def start(self):
        """Start the daemon."""
        # Check if already running
        if os.path.exists(self.pidfile):
            with open(self.pidfile, "r") as f:
                pid = int(f.read().strip())

            try:
                os.kill(pid, 0)  # Check if process exists
                print(f"Daemon already running with PID {pid}")
                return
            except OSError:
                # Process doesn't exist, remove stale pidfile
                os.remove(self.pidfile)

        print("Starting activity tracker daemon...")
        self.daemonize()

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Start the tracker
        self.tracker = ActivityTracker()
        self.tracker.start()

    def stop(self):
        """Stop the daemon."""
        if not os.path.exists(self.pidfile):
            print("Daemon not running")
            return

        with open(self.pidfile, "r") as f:
            pid = int(f.read().strip())

        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped daemon with PID {pid}")
            os.remove(self.pidfile)
        except OSError as e:
            print(f"Error stopping daemon: {e}")

    def status(self):
        """Check daemon status."""
        if not os.path.exists(self.pidfile):
            print("Daemon not running")
            return

        with open(self.pidfile, "r") as f:
            pid = int(f.read().strip())

        try:
            os.kill(pid, 0)
            print(f"Daemon running with PID {pid}")
        except OSError:
            print("Daemon not running (stale pidfile)")
            os.remove(self.pidfile)

    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        if self.tracker:
            self.tracker.stop()
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
        sys.exit(0)


def main():
    """Main entry point for daemon control."""
    daemon = ActivityDaemon()

    if len(sys.argv) != 2:
        print("Usage: python daemon.py {start|stop|restart|status}")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        daemon.start()
    elif command == "stop":
        daemon.stop()
    elif command == "restart":
        daemon.stop()
        time.sleep(1)
        daemon.start()
    elif command == "status":
        daemon.status()
    else:
        print("Unknown command. Use: start|stop|restart|status")
        sys.exit(1)


if __name__ == "__main__":
    main()
