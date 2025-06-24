#!/usr/bin/env python3
"""
Main entry point for the activity tracker module.
This allows running the module with: python -m activity_tracker
"""

import sys
from pathlib import Path

from .menu_bar import main

# Add the current directory to Python path if needed
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    main()
