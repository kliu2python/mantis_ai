#!/usr/bin/env python3
"""
Test script for scanning a specific Mantis project using custom project cookies
Runs in unheaded mode for visual verification
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from typing import List, Dict, Any
import time

# ========= 🔧 CONFIG ========= #
MANTIS_BASE_URL = os.environ.get('MANTIS_BASE_URL', 'https://mantis.fortinet.com/')
COOKIE_FILE = "cookies.json"
SQLITE_DB_FILE = "mantis_data.db"

# Performance configuration
PAGE_WORKERS = 1  # Single worker for testing
ISSUE_WORKERS = 3  # Limited workers for testing
PAGES_TO_SCAN = 3  # Limit pages for testing
DB_COMMIT_BATCH_SIZE = 10  # Smaller batch size for testing

# ========= 🗄️ SQLite Database Integration ========= #
def init_database():
    """Initialize SQLite database with required tables"""
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Create issues table - focused on correct project info from Category
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id TEXT UNIQUE,
                project_id TEXT,
                project_name TEXT,
                url TEXT,
                category TEXT,
                summary TEXT,
                description TEXT,
                steps_to_reproduce TEXT,
                additional_information TEXT,
                status TEXT,
                resolution TEXT,
                reporter TEXT,
                assigned_to TEXT,
                priority TEXT,
                severity TEXT,
                date_submitted TEXT,
                last_updated TEXT,
                version TEXT,
                fixed_in_version TEXT,
                target_version TEXT,
                bugnotes TEXT,
                scraped_at TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        print("SQLite database initialized successfully")
        return True

    except Exception as e:
        print(f"Error initializing SQLite database: {e}")
        return False

def store_issues_data_batch(issues_data: List[Dict[str, Any]]) -> bool:
    """Store issues data in SQLite database in batches for better performance"""
    if not issues_data:
        print("No issues data to store")
        return True

    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        print(f"Attempting to store batch of {len(issues_data)} issues in SQLite...")

        # Prepare data for batch insert
        data_to_insert = []
        for issue_data in issues_data:
            # Convert bugnotes to JSON string if it exists
            bugnotes_str = json.dumps(issue_data.get('bugnotes', [])) if issue_data.get('bugnotes') else None

            data_to_insert.append((
                issue_data.get('issue_id'),
                issue_data.get('project_id'),
                issue_data.get('project_name'),
                issue_data.get('url'),
                issue_data.get('category'),
                issue_data.get('summary'),
                issue_data.get('description'),
                issue_data.get('steps_to_reproduce'),
                issue_data.get('additional_information'),
                issue_data.get('status'),
                issue_data.get('resolution'),
                issue_data.get('reporter'),
                issue_data.get('assigned_to'),
                issue_data.get('priority'),
                issue_data.get('severity'),
                issue_data.get('date_submitted'),
                issue_data.get('last_updated'),
                issue_data.get('version'),
                issue_data.get('fixed_in_version'),
                issue_data.get('target_version'),
                bugnotes_str,
                issue_data.get('scraped_at')
            ))

        # Batch insert using executemany for better performance
        cursor.executemany("""
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
        print(f"Successfully stored batch of {len(issues_data)} issues in SQLite")
        return True

    except Exception as e:
        print(f"Error storing issues data in SQLite: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========= 🔍 Page Collection Logic ========= #
def get_issue_urls_from_page_worker(page_number: int, context_args: Dict, project_cookie: str = None) -> List[Dict[str, str]]:
    """
    Worker function to extract issue URLs from a specific page
    Runs in unheaded mode for visual verification
    """
    issue_urls = []

    try:
        print(f"  Processing page {page_number}")

        # Update cookies with specific project cookie if provided
        if project_cookie and 'storage_state' in context_args:
            # Add or update the project cookie
            project_cookie_obj = {
                "name": "MANTIS_PROJECT_COOKIE",
                "value": project_cookie,
                "domain": ".mantis.fortinet.com",
                "path": "/"
            }

            # Check if MANTIS_PROJECT_COOKIE already exists and update it
            cookies = context_args['storage_state'].get('cookies', [])
            project_cookie_found = False
            for i, cookie in enumerate(cookies):
                if cookie.get('name') == 'MANTIS_PROJECT_COOKIE':
                    cookies[i] = project_cookie_obj
                    project_cookie_found = True
                    break

            # If not found, append it
            if not project_cookie_found:
                cookies.append(project_cookie_obj)

            context_args['storage_state']['cookies'] = cookies

        with sync_playwright() as p:
            # Run in headed mode for visual verification
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the specific page
            page_url = f"{MANTIS_BASE_URL}view_all_bug_page.php?page_number={page_number}"
            print(f"    Navigating to: {page_url}")
            page.goto(page_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)  # Wait 1 second to observe

            # Verify we're on the correct project page
            current_url = page.url
            print(f"    Current page URL: {current_url}")

            # Check if project cookie is applied by looking for project-specific elements
            project_selector = page.query_selector("select[name='project_id']")
            if project_selector:
                selected_option = project_selector.query_selector("option:checked")
                if selected_option:
                    project_text = selected_option.text_content().strip()
                    print(f"    Current project: {project_text}")

            # Find the main bug list table
            tables = page.query_selector_all("table")

            if len(tables) >= 4:
                bug_table = tables[3]  # Table 4 (0-indexed)
                rows = bug_table.query_selector_all("tr")

                # Extract issue URLs
                for i in range(2, len(rows)):  # Start from row 2 (skip headers)
                    row = rows[i]
                    cells = row.query_selector_all("td")

                    # Only process rows with sufficient cells
                    if len(cells) >= 30:
                        issue_id = cells[1].text_content().strip()

                        # Only process rows with valid issue IDs
                        if issue_id and issue_id.isdigit():
                            id_cell = cells[1]
                            id_link = id_cell.query_selector("a")
                            if id_link:
                                issue_url = id_link.get_attribute("href")
                                if issue_url:
                                    # Construct full URL
                                    full_url = f"{MANTIS_BASE_URL}{issue_url}"
                                    issue_urls.append({
                                        "issue_id": issue_id,
                                        "url": full_url
                                    })

            page.close()
            browser.close()

    except Exception as e:
        print(f"Error getting issue URLs from page {page_number}: {e}")
        import traceback
        traceback.print_exc()

    return issue_urls

# ========= 🔍 Issue Processing Logic ========= #
def extract_complete_issue_details(issue_info: Dict[str, str], context_args: Dict) -> Dict[str, Any]:
    """
    Click into an issue and extract complete detailed information
    Gets the CORRECT project information from the Category field
    """
    issue_url = issue_info.get("url")
    if not issue_url:
        return {}

    issue_data = {
        "url": issue_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_info.get("issue_id")
    }

    try:
        print(f"    Extracting details from: {issue_url}")

        with sync_playwright() as p:
            # Run in headed mode for visual verification
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the issue page with timeout handling
            page.goto(issue_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(1000)  # Wait 1 second to observe

            # Extract information using targeted selectors
            # Find tables that contain issue information
            tables = page.query_selector_all("table")

            # Process tables looking for issue data
            for table in tables:
                rows = table.query_selector_all("tr")

                # Process each row looking for label/value pairs
                for row in rows:
                    cells = row.query_selector_all("td, th")

                    # Look for rows with 2+ cells where first might be a label
                    if len(cells) >= 2:
                        first_cell_text = cells[0].text_content().strip().lower()
                        second_cell_text = cells[1].text_content().strip()

                        # Map common field names
                        field_mapping = {
                            'category': 'category',
                            'summary': 'summary',
                            'description': 'description',
                            'steps to reproduce': 'steps_to_reproduce',
                            'additional information': 'additional_information',
                            'status': 'status',
                            'resolution': 'resolution',
                            'reporter': 'reporter',
                            'assigned to': 'assigned_to',
                            'priority': 'priority',
                            'severity': 'severity',
                            'date submitted': 'date_submitted',
                            'last updated': 'last_updated',
                            'version': 'version',
                            'fixed in version': 'fixed_in_version',
                            'target version': 'target_version',
                        }

                        # Match field and store value
                        for label_pattern, field_name in field_mapping.items():
                            if label_pattern in first_cell_text and second_cell_text:
                                issue_data[field_name] = second_cell_text

                        # Special handling for the issue structure we observed:
                        # Look for header row with 'id' in first cell and 'category' in second cell
                        if first_cell_text == 'id' and 'category' in second_cell_text.lower():
                            # The next row should contain the actual data
                            # The category value is in the second cell of the next row
                            next_row = row.query_selector("~ tr")  # Next sibling tr
                            if next_row:
                                next_cells = next_row.query_selector_all("td, th")
                                if len(next_cells) >= 2:
                                    # The category value is in the second cell of the next row
                                    category_value = next_cells[1].text_content().strip()
                                    if category_value:
                                        issue_data['category'] = category_value

            # Extract project information from category
            category = issue_data.get('category', '')
            if category:
                # Extract project name from category
                # Handle formats like "[FortiIdentity Cloud] Registration" or "FortiIdentity Cloud"
                if '[' in category and ']' in category:
                    # Extract project name from brackets
                    start = category.find('[') + 1
                    end = category.find(']')
                    if start > 0 and end > start:
                        project_name = category[start:end].strip()
                        issue_data['project_name'] = project_name
                else:
                    # Use first word as project name if no brackets
                    project_name = category.split()[0] if category.split() else category
                    issue_data['project_name'] = project_name

            # Extract bugnotes specifically
            bugnotes = []
            bugnotes_section = page.query_selector("#bugnotes, .bugnotes")

            if bugnotes_section:
                bugnote_elements = bugnotes_section.query_selector_all(".bugnote")

                for bugnote_element in bugnote_elements:
                    bugnote_data = {}

                    # Try to extract bugnote information
                    # Author - look for text with parentheses
                    author_element = bugnote_element.query_selector(".bugnoteheader")
                    if author_element:
                        author_text = author_element.text_content().strip()
                        bugnote_data["author"] = author_text

                    # Date - look for date information
                    date_candidates = bugnote_element.query_selector_all("*")
                    for candidate in date_candidates:
                        text = candidate.text_content().strip()
                        # Look for date-like patterns
                        if (':' in text and len(text) > 10) or ('-' in text and len(text) > 8):
                            # Additional check to avoid button text
                            if '[' not in text and ']' not in text:
                                bugnote_data["date"] = text
                                break

                    # Content - look for substantial text
                    content_element = bugnote_element.query_selector(".bugnote-note")
                    if content_element:
                        content_text = content_element.text_content().strip()
                        if len(content_text) > 5:
                            bugnote_data["content"] = content_text

                    if bugnote_data:
                        bugnotes.append(bugnote_data)

                if bugnotes:
                    issue_data["bugnotes"] = bugnotes

            page.close()
            browser.close()

    except Exception as e:
        print(f"Error extracting issue details from {issue_url}: {e}")
        import traceback
        traceback.print_exc()
        return {}

    return issue_data

# ========= 🚀 Test Project Scanning Functions ========= #
def scan_project_issues(project_cookie: str = None):
    """
    Test function to scan issues from a specific project using custom project cookies
    Runs in unheaded mode for visual verification
    """
    print("Starting Test Project Scanner...")
    print(f"Project cookie: {project_cookie}")
    print("Running in headed (unheaded) mode for visual verification")

    # Initialize database
    if not init_database():
        print("Failed to initialize database")
        return False

    # Load existing cookies for authentication
    context_args = {}
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    context_args['storage_state'] = {
                        "cookies": cookies_data['cookies'],
                        "origins": cookies_data.get("origins", [])
                    }
        except Exception as e:
            print(f"Could not load cookies: {e}")

    try:
        # Collect issue URLs from pages (limited for testing)
        print(f"\n=== PHASE 1: Collecting issue URLs from first {PAGES_TO_SCAN} pages ===")
        start_time = time.time()

        all_issue_urls = []
        for page_num in range(1, PAGES_TO_SCAN + 1):
            page_issues = get_issue_urls_from_page_worker(page_num, context_args, project_cookie)
            all_issue_urls.extend(page_issues)
            print(f"  Collected {len(page_issues)} issues from page {page_num}")

            # Small delay between pages
            time.sleep(1)

        collection_time = time.time() - start_time
        print(f"\nCollected {len(all_issue_urls)} issue URLs in {collection_time:.1f} seconds")

        # Process collected issues
        print(f"\n=== PHASE 2: Extracting detailed information from {len(all_issue_urls)} issues ===")
        start_time = time.time()

        processed_issues = []
        for i, issue_info in enumerate(all_issue_urls[:10]):  # Limit to first 10 for testing
            print(f"  Processing issue {i+1}/{min(len(all_issue_urls), 10)}: {issue_info.get('issue_id')}")
            detailed_issue = extract_complete_issue_details(issue_info, context_args)
            if detailed_issue:
                processed_issues.append(detailed_issue)

            # Small delay between issues
            time.sleep(1)

        processing_time = time.time() - start_time

        # Store issues in database
        if processed_issues:
            print(f"\n=== PHASE 3: Storing {len(processed_issues)} issues in database ===")
            success = store_issues_data_batch(processed_issues)
            if success:
                print("Successfully stored issues in database")
            else:
                print("Failed to store issues in database")
        else:
            print("No issues to store in database")

        print(f"\n=== SCAN COMPLETE ===")
        print(f"Processed {len(processed_issues)} issues in {processing_time:.1f} seconds")
        rate = len(processed_issues) / processing_time if processing_time > 0 else 0
        print(f"Processing rate: {rate:.1f} issues/sec")

        # Show sample of collected data
        if processed_issues:
            print("\nSample of collected issues:")
            for issue in processed_issues[:3]:
                print(f"  - Issue ID: {issue.get('issue_id')}")
                print(f"    Project: {issue.get('project_name')}")
                print(f"    Category: {issue.get('category')}")
                print(f"    Summary: {issue.get('summary')[:50]}...")
                print()

        return True

    except Exception as e:
        print(f"Error in test scanning process: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========= ▶ Entry Point ========= #
if __name__ == "__main__":
    # You can specify a project cookie here for testing
    # For FortiToken project, you would use its specific cookie value
    PROJECT_COOKIE = None  # Set to specific project cookie value if needed

    scan_project_issues(PROJECT_COOKIE)