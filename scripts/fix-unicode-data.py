#!/usr/bin/env python3
"""
Fix Unicode in existing activity data files by re-saving them with proper encoding.
This script loads JSON files (which automatically converts escape sequences to Unicode)
and saves them back with ensure_ascii=False.
"""

import json
import sys
from pathlib import Path


def fix_data_files(data_dir: Path) -> dict:
    """Fix Unicode encoding in all activity data files."""
    if not data_dir.exists():
        print(f"Directory does not exist: {data_dir}")
        return {"fixed": 0, "skipped": 0, "errors": 0}

    activity_files = list(data_dir.glob("activity_*.json"))
    if not activity_files:
        print(f"No activity files found in {data_dir}")
        return {"fixed": 0, "skipped": 0, "errors": 0}

    print(f"Processing {len(activity_files)} activity files...")

    results = {"fixed": 0, "skipped": 0, "errors": 0}

    for file_path in sorted(activity_files):
        try:
            # Read the file (JSON automatically converts escape sequences)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Write it back with proper Unicode encoding
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            results["fixed"] += 1

            # Check if there were Unicode characters
            has_unicode = any(
                "·" in key or "—" in key or "*" in key for key in data.keys()
            )
            if has_unicode:
                print(f"[OK] Fixed Unicode in: {file_path.name}")

        except Exception as e:
            print(f"[FAIL] Error processing {file_path}: {e}")
            results["errors"] += 1

    return results


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python fix-unicode-data.py <data_directory>")
        print("Example: python fix-unicode-data.py activity_data")
        return

    data_dir = Path(sys.argv[1])
    print(f"Fixing Unicode encoding in: {data_dir}")

    results = fix_data_files(data_dir)

    print("\nResults:")
    print(f"  Fixed: {results['fixed']} files")
    print(f"  Errors: {results['errors']} files")

    if results["fixed"] > 0:
        print("[OK] All files now use proper Unicode encoding!")


if __name__ == "__main__":
    main()
