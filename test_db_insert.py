#!/usr/bin/env python3
"""
Test script to verify database insertion works correctly
"""

import sqlite3
import json
from datetime import datetime, timezone

# Configuration from cached_high_performance_scanner.py
SQLITE_DB_FILE = "mantis_data.db"

def test_database_insertion():
    """Test database insertion with sample data"""
    # Sample issue data
    sample_issue = {
        'issue_id': 'TEST001',
        'project_id': 'PROJ001',
        'project_name': 'Test Project',
        'url': 'https://mantis.example.com/view.php?id=TEST001',
        'category': 'Test Category',
        'summary': 'Test issue summary',
        'description': 'Test issue description',
        'steps_to_reproduce': 'Step 1: Do something\nStep 2: Do something else',
        'additional_information': 'Additional test information',
        'status': 'NEW',
        'resolution': 'OPEN',
        'reporter': 'test_user',
        'assigned_to': 'developer',
        'priority': 'normal',
        'severity': 'minor',
        'date_submitted': '2023-01-01 10:00:00',
        'last_updated': '2023-01-01 10:00:00',
        'version': '1.0',
        'fixed_in_version': '',
        'target_version': '',
        'bugnotes': json.dumps([{'author': 'tester', 'date': '2023-01-01', 'content': 'Test note'}]),
        'scraped_at': datetime.now(timezone.utc).isoformat()
    }

    # Try to insert into database
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        print(f"Inserting test issue {sample_issue['issue_id']} into database...")

        # Prepare data for insert
        data_to_insert = (
            sample_issue.get('issue_id'),
            sample_issue.get('project_id'),
            sample_issue.get('project_name'),
            sample_issue.get('url'),
            sample_issue.get('category'),
            sample_issue.get('summary'),
            sample_issue.get('description'),
            sample_issue.get('steps_to_reproduce'),
            sample_issue.get('additional_information'),
            sample_issue.get('status'),
            sample_issue.get('resolution'),
            sample_issue.get('reporter'),
            sample_issue.get('assigned_to'),
            sample_issue.get('priority'),
            sample_issue.get('severity'),
            sample_issue.get('date_submitted'),
            sample_issue.get('last_updated'),
            sample_issue.get('version'),
            sample_issue.get('fixed_in_version'),
            sample_issue.get('target_version'),
            sample_issue.get('bugnotes'),
            sample_issue.get('scraped_at')
        )

        # Insert using the same query as in the main code
        cursor.execute("""
            INSERT OR REPLACE INTO issues (
                issue_id, project_id, project_name, url, category, summary, description,
                steps_to_reproduce, additional_information, status, resolution,
                reporter, assigned_to, priority, severity, date_submitted,
                last_updated, version, fixed_in_version, target_version,
                bugnotes, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data_to_insert)

        conn.commit()
        conn.close()
        print("Successfully inserted test issue into database")
        return True

    except Exception as e:
        print(f"Error inserting test issue into database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_database_insertion()