#!/usr/bin/env python3
"""
Status checker for FortiToken project data
"""

import sqlite3
import os
from datetime import datetime

SQLITE_DB_FILE = "mantis_data.db"

def check_fortitoken_status():
    """Check the current status of FortiToken project data"""
    print("=== FortiToken Project Status ===")

    if not os.path.exists(SQLITE_DB_FILE):
        print(f"Database file {SQLITE_DB_FILE} not found!")
        return

    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Check if the FortiToken table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%FortiToken%'
        """)
        tables = cursor.fetchall()

        if not tables:
            print("No FortiToken tables found in database")
            conn.close()
            return

        print("Found FortiToken tables:")
        for table in tables:
            table_name = table[0]
            print(f"  - {table_name}")

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    Rows: {count}")

            # Get date range
            cursor.execute(f"SELECT MIN(scraped_at), MAX(scraped_at) FROM {table_name}")
            min_date, max_date = cursor.fetchone()
            print(f"    First scan: {min_date or 'N/A'}")
            print(f"    Last scan:  {max_date or 'N/A'}")

            # Show sample data
            print("    Sample issues:")
            cursor.execute(f"""
                SELECT issue_id, summary, last_updated
                FROM {table_name}
                ORDER BY last_updated DESC
                LIMIT 3
            """)
            samples = cursor.fetchall()
            for issue_id, summary, last_updated in samples:
                print(f"      {issue_id}: {summary[:50]}... ({last_updated})")

            print()

        conn.close()

    except Exception as e:
        print(f"Error checking FortiToken status: {e}")
        import traceback
        traceback.print_exc()

def show_recent_issues(limit=10):
    """Show the most recently scanned FortiToken issues"""
    print(f"\n=== {limit} Most Recent FortiToken Issues ===")

    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Find the FortiToken table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%FortiToken%'
        """)
        tables = cursor.fetchall()

        if not tables:
            print("No FortiToken tables found")
            conn.close()
            return

        table_name = tables[0][0]  # Use the first FortiToken table found

        # Get recent issues
        cursor.execute(f"""
            SELECT issue_id, summary, status, last_updated, scraped_at
            FROM {table_name}
            ORDER BY scraped_at DESC
            LIMIT {limit}
        """)

        issues = cursor.fetchall()

        print(f"{'ID':<10} {'Status':<12} {'Last Updated':<20} {'Scraped At':<20} {'Summary'}")
        print("-" * 100)

        for issue_id, summary, status, last_updated, scraped_at in issues:
            # Clean up dates for display
            last_updated_clean = last_updated[:10] if last_updated else 'N/A'
            scraped_at_clean = scraped_at[:19] if scraped_at else 'N/A'

            print(f"{issue_id:<10} {status:<12} {last_updated_clean:<20} {scraped_at_clean:<20} {summary[:30]}")

        conn.close()

    except Exception as e:
        print(f"Error showing recent issues: {e}")
        import traceback
        traceback.print_exc()

def show_statistics():
    """Show statistics for FortiToken project data"""
    print("\n=== FortiToken Project Statistics ===")

    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Find the FortiToken table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%FortiToken%'
        """)
        tables = cursor.fetchall()

        if not tables:
            print("No FortiToken tables found")
            conn.close()
            return

        table_name = tables[0][0]  # Use the first FortiToken table found

        # Total issues
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_issues = cursor.fetchone()[0]
        print(f"Total Issues: {total_issues}")

        # Status distribution
        print("\nStatus Distribution:")
        cursor.execute(f"""
            SELECT status, COUNT(*)
            FROM {table_name}
            GROUP BY status
            ORDER BY COUNT(*) DESC
        """)
        status_dist = cursor.fetchall()
        for status, count in status_dist:
            print(f"  {status or 'NULL':<15}: {count}")

        # Severity distribution
        print("\nSeverity Distribution:")
        cursor.execute(f"""
            SELECT severity, COUNT(*)
            FROM {table_name}
            GROUP BY severity
            ORDER BY COUNT(*) DESC
        """)
        severity_dist = cursor.fetchall()
        for severity, count in severity_dist:
            print(f"  {severity or 'NULL':<15}: {count}")

        # Date range
        cursor.execute(f"SELECT MIN(last_updated), MAX(last_updated) FROM {table_name}")
        min_date, max_date = cursor.fetchone()
        print(f"\nDate Range:")
        print(f"  Oldest Issue: {min_date or 'N/A'}")
        print(f"  Newest Issue: {max_date or 'N/A'}")

        conn.close()

    except Exception as e:
        print(f"Error showing statistics: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    check_fortitoken_status()
    show_statistics()
    show_recent_issues(10)

if __name__ == "__main__":
    main()