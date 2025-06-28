#!/usr/bin/env python3
"""
Main entry point for the activity tracker module.
This allows running the module with: python -m activity_tracker
"""

import sys
from pathlib import Path

# Add the current directory to Python path if needed
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import using absolute import for PyInstaller compatibility
try:
    from activity_tracker.menu_bar import main
except ImportError:
    # Fallback for relative import when running as module
    from .menu_bar import main

if __name__ == "__main__":
    main()
