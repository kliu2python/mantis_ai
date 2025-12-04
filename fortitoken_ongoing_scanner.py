#!/usr/bin/env python3
"""
Ongoing Scanner for FortiToken Project
Continuously scans the FortiToken project (ID 153) and updates the database
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
import time
from fast_project_scanner import scan_project_issues_fast

# ========= 🔧 CONFIG ========= #
PROJECT_ID = "153"  # FortiToken project ID
PROJECT_NAME = "FortiToken"
MAX_PAGES = 200    # Scan up to 200 pages (adjust as needed)
SCAN_INTERVAL = 3600  # 1 hour between scans (in seconds)

# Database file
SQLITE_DB_FILE = "mantis_data.db"

def get_last_scan_time() -> datetime:
    """Get the timestamp of the last scan for this project"""
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Try to get the latest scraped_at timestamp from the project table
        table_name = "issues_FortiToken"
        cursor.execute(f"SELECT MAX(scraped_at) FROM {table_name}")
        result = cursor.fetchone()

        conn.close()

        if result and result[0]:
            # Parse the ISO format timestamp
            return datetime.fromisoformat(result[0].replace('Z', '+00:00'))
        else:
            # If no records, return a long time ago
            return datetime.fromtimestamp(0, tz=timezone.utc)

    except Exception as e:
        print(f"Error getting last scan time: {e}")
        # If error, return a long time ago to ensure scan runs
        return datetime.fromtimestamp(0, tz=timezone.utc)

def get_issue_count() -> int:
    """Get current count of issues in the database for this project"""
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        table_name = "issues_FortiToken"
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        result = cursor.fetchone()

        conn.close()

        return result[0] if result else 0

    except Exception as e:
        print(f"Error getting issue count: {e}")
        return 0

def main():
    """Main function for ongoing FortiToken scanning"""
    print("=== FortiToken Ongoing Scanner ===")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Project Name: {PROJECT_NAME}")
    print(f"Max Pages per Scan: {MAX_PAGES}")
    print(f"Scan Interval: {SCAN_INTERVAL/3600:.1f} hours")
    print()

    scan_count = 0

    while True:
        scan_count += 1
        print(f"\n=== SCAN #{scan_count} STARTING ===")
        print(f"Current time: {datetime.now().isoformat()}")

        # Show current database status
        current_count = get_issue_count()
        print(f"Current database contains {current_count} FortiToken issues")

        # Perform the scan
        start_time = time.time()
        print(f"Starting scan of FortiToken project...")

        try:
            success = scan_project_issues_fast(PROJECT_ID, MAX_PAGES)

            end_time = time.time()
            scan_duration = end_time - start_time

            if success:
                print(f"✅ Scan #{scan_count} completed successfully!")
                new_count = get_issue_count()
                print(f"   Issues in database: {new_count} ({new_count - current_count:+d})")
                print(f"   Scan duration: {scan_duration:.1f} seconds")
            else:
                print(f"❌ Scan #{scan_count} failed!")

        except Exception as e:
            print(f"❌ Scan #{scan_count} failed with exception: {e}")
            import traceback
            traceback.print_exc()

        # Wait for next scan
        print(f"\nWaiting {SCAN_INTERVAL/3600:.1f} hours until next scan...")
        print("=" * 50)

        # Sleep until next scan (unless interrupted)
        try:
            time.sleep(SCAN_INTERVAL)
        except KeyboardInterrupt:
            print("\nScanner interrupted by user")
            break

if __name__ == "__main__":
    main()