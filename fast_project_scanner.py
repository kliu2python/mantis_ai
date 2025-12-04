#!/usr/bin/env python3
"""
Fast Project-specific Mantis Scanner using Multiprocessing
Accepts project cookies, validates against cookies.json, updates if needed,
and fetches issues for that specific project using parallel processing.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from typing import List, Dict, Any
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import math
import sys

# ========= 🔧 CONFIG ========= #
MANTIS_BASE_URL = os.environ.get('MANTIS_BASE_URL', 'https://mantis.fortinet.com/')
COOKIE_FILE = "cookies.json"
SQLITE_DB_FILE = "mantis_data.db"

# Performance configuration - HIGH SPEED SETTINGS
PAGE_WORKERS = 8  # Number of concurrent workers for page collection
ISSUE_WORKERS = 20  # Number of concurrent workers for issue processing
PAGES_PER_BATCH = 50  # Process pages in batches
DB_COMMIT_BATCH_SIZE = 100  # Larger batch size for database commits

# Rate limiting configuration - OPTIMIZED FOR SPEED
REQUEST_DELAY = 0.1  # Minimal delay between requests
MAX_RETRIES = 2  # Fewer retries for speed

# ========= 🗄️ SQLite Database Integration ========= #
def init_project_database(project_name: str):
    """Initialize SQLite database with project-specific table"""
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Create project-specific table
        table_name = f"issues_{project_name.replace(' ', '_').replace('-', '_').replace('.', '_')}"
        table_name = ''.join(c for c in table_name if c.isalnum() or c in '_')

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
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
        print(f"Database table '{table_name}' initialized successfully")
        return table_name

    except Exception as e:
        print(f"Error initializing project database: {e}")
        return None

def store_project_issues_data_batch(issues_data: List[Dict[str, Any]], table_name: str) -> bool:
    """Store project issues data in SQLite database in batches"""
    if not issues_data:
        print("No issues data to store")
        return True

    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        print(f"Attempting to store batch of {len(issues_data)} issues in table '{table_name}'...")

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
        cursor.executemany(f"""
            INSERT OR REPLACE INTO {table_name} (
                issue_id, project_id, project_name, url, category, summary, description,
                steps_to_reproduce, additional_information, status, resolution,
                reporter, assigned_to, priority, severity, date_submitted,
                last_updated, version, fixed_in_version, target_version,
                bugnotes, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data_to_insert)

        conn.commit()
        conn.close()
        print(f"Successfully stored batch of {len(issues_data)} issues in table '{table_name}'")
        return True

    except Exception as e:
        print(f"Error storing project issues data: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========= 🍪 Cookie Management ========= #
def load_cookies():
    """Load cookies from file"""
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                return cookies_data
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return None
    else:
        print(f"Cookie file {COOKIE_FILE} not found")
        return None

def update_project_cookie(cookies_data: Dict, project_cookie_value: str) -> Dict:
    """Update or add project cookie to cookies data"""
    if not cookies_data:
        return cookies_data

    # Work with a copy to avoid modifying original
    updated_cookies = json.loads(json.dumps(cookies_data))

    # Check if cookies are in storage_state format
    if 'cookies' in updated_cookies:
        cookies = updated_cookies['cookies']
    else:
        # Direct cookies array
        cookies = updated_cookies if isinstance(updated_cookies, list) else []

    # Find and update MANTIS_PROJECT_COOKIE or add it
    project_cookie_found = False
    for cookie in cookies:
        if cookie.get('name') == 'MANTIS_PROJECT_COOKIE':
            cookie['value'] = str(project_cookie_value)
            project_cookie_found = True
            break

    # If not found, add it
    if not project_cookie_found:
        cookies.append({
            "name": "MANTIS_PROJECT_COOKIE",
            "value": str(project_cookie_value),
            "domain": ".mantis.fortinet.com",
            "path": "/"
        })

    # Update the cookies in the structure
    if 'cookies' in updated_cookies:
        updated_cookies['cookies'] = cookies
    else:
        updated_cookies = cookies

    return updated_cookies

def save_cookies(cookies_data: Dict):
    """Save cookies back to file"""
    try:
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies_data, f, indent=2)
        print(f"Updated cookies saved to {COOKIE_FILE}")
        return True
    except Exception as e:
        print(f"Error saving cookies: {e}")
        return False

# ========= 🔍 Project Validation ========= #
def validate_project_cookie(project_cookie_value: str, context_args: Dict) -> tuple:
    """
    Validate that the project cookie works and get project name
    Returns (is_valid: bool, project_name: str)
    """
    try:
        print(f"Validating project cookie: {project_cookie_value}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the main page
            page.goto(MANTIS_BASE_URL, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)  # Wait a moment

            # Check current project
            project_selector = page.query_selector("select[name='project_id']")
            if project_selector:
                selected_option = project_selector.query_selector("option:checked")
                if selected_option:
                    project_text = selected_option.text_content().strip()
                    project_value = selected_option.get_attribute("value")

                    print(f"Current project: {project_text} (ID: {project_value})")

                    # Check if it matches expected project
                    if project_value == str(project_cookie_value):
                        page.close()
                        browser.close()
                        return True, project_text
                    else:
                        print(f"Mismatch: Expected {project_cookie_value}, got {project_value}")

            page.close()
            browser.close()

    except Exception as e:
        print(f"Error validating project cookie: {e}")

    return False, "Unknown_Project"

# ========= 🔍 Page Collection Logic (Multiprocessing) ========= #
def get_issue_urls_from_page_worker(page_number: int, context_args_serialized: str, project_cookie_value: str) -> List[Dict[str, str]]:
    """
    Worker function to extract issue URLs from a specific page
    Runs in a separate Playwright context
    """
    # Deserialize context args
    context_args = json.loads(context_args_serialized)

    # Ensure project cookie is set
    if 'storage_state' in context_args:
        cookies = context_args['storage_state'].get('cookies', [])
        project_cookie_found = False
        for cookie in cookies:
            if cookie.get('name') == 'MANTIS_PROJECT_COOKIE':
                cookie['value'] = str(project_cookie_value)
                project_cookie_found = True
                break
        if not project_cookie_found:
            cookies.append({
                "name": "MANTIS_PROJECT_COOKIE",
                "value": str(project_cookie_value),
                "domain": ".mantis.fortinet.com",
                "path": "/"
            })
        context_args['storage_state']['cookies'] = cookies

    issue_urls = []

    try:
        print(f"  Processing page {page_number}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the specific page
            page_url = f"{MANTIS_BASE_URL}view_all_bug_page.php?page_number={page_number}"
            page.goto(page_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(REQUEST_DELAY)  # Minimal wait

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

    return issue_urls

def collect_project_issue_urls_parallel(context_args: Dict, project_cookie_value: str, max_pages: int) -> List[Dict[str, str]]:
    """
    Collect all issue URLs from project pages using multiprocessing
    """
    print(f"Collecting issue URLs from project using {PAGE_WORKERS} workers...")
    print(f"Processing up to {max_pages} pages")

    all_issue_urls = []

    # Process pages in batches
    batch_size = PAGE_WORKERS * 5  # Process pages in batches
    total_batches = math.ceil(max_pages / batch_size)

    print(f"Processing {max_pages} pages in {total_batches} batches of {batch_size} pages each")

    # Serialize context args for passing to workers
    context_args_serialized = json.dumps(context_args)

    for batch_num in range(total_batches):
        start_page = batch_num * batch_size + 1
        end_page = min((batch_num + 1) * batch_size, max_pages)

        print(f"Processing batch {batch_num + 1}/{total_batches}: pages {start_page}-{end_page}")

        # Create page numbers for this batch
        page_numbers = list(range(start_page, end_page + 1))

        # Use ProcessPoolExecutor for concurrent page processing
        with ProcessPoolExecutor(max_workers=PAGE_WORKERS) as executor:
            # Submit all page processing tasks
            future_to_page = {
                executor.submit(get_issue_urls_from_page_worker, page_num, context_args_serialized, project_cookie_value): page_num
                for page_num in page_numbers
            }

            # Collect results as they complete
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_issues = future.result()
                    all_issue_urls.extend(page_issues)
                except Exception as e:
                    print(f"Page {page_num} generated an exception: {e}")

        print(f"Completed batch {batch_num + 1}. Total issues so far: {len(all_issue_urls)}")

    print(f"Collected {len(all_issue_urls)} issue URLs from {max_pages} pages")
    return all_issue_urls

# ========= 🔍 Issue Processing Logic (Multiprocessing) ========= #
def extract_project_issue_details_worker(issue_info: Dict[str, str], context_args_serialized: str) -> Dict[str, Any]:
    """
    Worker function to extract detailed information for a project issue
    """
    # Deserialize context args
    context_args = json.loads(context_args_serialized)

    issue_url = issue_info.get("url")
    if not issue_url:
        return {}

    issue_data = {
        "url": issue_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_info.get("issue_id")
    }

    # Implement retry mechanism
    for attempt in range(MAX_RETRIES):
        try:
            # Add minimal rate limiting delay
            time.sleep(REQUEST_DELAY)

            # Import playwright inside the function to avoid context issues
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(**context_args)
                page = context.new_page()

                # Navigate to the issue page with timeout handling
                page.goto(issue_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(REQUEST_DELAY / 2)  # Minimal wait

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

                return issue_data

        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {issue_url}: {e}")
            if attempt < MAX_RETRIES - 1:
                # Minimal backoff
                time.sleep(REQUEST_DELAY * 2)
            else:
                print(f"Failed to extract issue details for {issue_url} after {MAX_RETRIES} attempts")
                # Return basic issue data
                return issue_data

    return issue_data

def process_issues_parallel(issue_urls: List[Dict[str, str]], context_args: Dict) -> List[Dict[str, Any]]:
    """
    Process issues using multiple worker processes with batch processing
    """
    print(f"Starting high-performance processing with {ISSUE_WORKERS} workers for {len(issue_urls)} issues")

    # Serialize context args for passing to workers
    context_args_serialized = json.dumps(context_args)

    # Use ProcessPoolExecutor for concurrent issue processing
    processed_issues = []

    with ProcessPoolExecutor(max_workers=ISSUE_WORKERS) as executor:
        # Submit all issue processing tasks
        future_to_issue = {
            executor.submit(extract_project_issue_details_worker, issue_info, context_args_serialized): issue_info
            for issue_info in issue_urls
        }

        # Collect results as they complete
        completed = 0
        start_time = time.time()

        for future in as_completed(future_to_issue):
            issue_info = future_to_issue[future]
            try:
                detailed_issue = future.result()
                if detailed_issue:
                    processed_issues.append(detailed_issue)

                completed += 1
                if completed % 10 == 0:  # Print progress every 10 issues
                    elapsed_time = time.time() - start_time
                    rate = completed / elapsed_time if elapsed_time > 0 else 0
                    print(f"Processed {completed}/{len(issue_urls)} issues ({rate:.1f} issues/sec)")

            except Exception as e:
                print(f"Issue {issue_info.get('issue_id')} generated an exception: {e}")

    print(f"Completed processing {len(processed_issues)} issues")
    return processed_issues

# ========= 🚀 Fast Project Scanner Functions ========= #
def scan_project_issues_fast(project_cookie_value: str, max_pages: int = 100):
    """
    Main function to scan issues for a specific project using multiprocessing
    """
    print(f"Starting FAST Project Scanner for project cookie: {project_cookie_value}")
    print(f"Will scan up to {max_pages} pages")
    print(f"Using {PAGE_WORKERS} page workers and {ISSUE_WORKERS} issue workers")

    # Load existing cookies
    cookies_data = load_cookies()
    if not cookies_data:
        print("Failed to load cookies, exiting")
        return False

    # Update cookies with project cookie
    print("Updating cookies with project cookie...")
    updated_cookies = update_project_cookie(cookies_data, project_cookie_value)

    # Save updated cookies
    if not save_cookies(updated_cookies):
        print("Failed to save updated cookies, continuing with loaded cookies")

    # Prepare context arguments
    context_args = {}
    if isinstance(updated_cookies, dict) and 'cookies' in updated_cookies:
        context_args['storage_state'] = {
            "cookies": updated_cookies['cookies'],
            "origins": updated_cookies.get("origins", [])
        }
    elif isinstance(updated_cookies, list):
        context_args['storage_state'] = {
            "cookies": updated_cookies,
            "origins": []
        }

    # Validate project cookie and get project name
    print("Validating project cookie...")
    is_valid, project_name = validate_project_cookie(project_cookie_value, context_args)

    if not is_valid:
        print("WARNING: Project cookie validation failed, continuing anyway...")
        project_name = f"Project_{project_cookie_value}"

    print(f"Project Name: {project_name}")

    # Initialize project-specific database table
    table_name = init_project_database(project_name)
    if not table_name:
        print("Failed to initialize project database")
        return False

    try:
        # Collect issue URLs from project using multiprocessing
        print(f"\n=== PHASE 1: Collecting issue URLs from project (multiprocessing) ===")
        start_time = time.time()

        all_issue_urls = collect_project_issue_urls_parallel(context_args, project_cookie_value, max_pages)

        collection_time = time.time() - start_time
        print(f"\nCollected {len(all_issue_urls)} issue URLs in {collection_time:.1f} seconds")
        print(f"Collection rate: {len(all_issue_urls)/collection_time:.1f} pages/sec")

        # Process collected issues using multiprocessing
        print(f"\n=== PHASE 2: Extracting detailed information from {len(all_issue_urls)} issues (multiprocessing) ===")
        start_time = time.time()

        processed_issues = process_issues_parallel(all_issue_urls, context_args)

        processing_time = time.time() - start_time

        # Store all processed issues
        print(f"\n=== PHASE 3: Storing {len(processed_issues)} issues in database ===")
        stored_count = 0

        # Process in batches for database storage
        for i in range(0, len(processed_issues), DB_COMMIT_BATCH_SIZE):
            batch = processed_issues[i:i + DB_COMMIT_BATCH_SIZE]
            success = store_project_issues_data_batch(batch, table_name)
            if success:
                stored_count += len(batch)
            print(f"Stored batch {i//DB_COMMIT_BATCH_SIZE + 1}/{math.ceil(len(processed_issues)/DB_COMMIT_BATCH_SIZE)}")

        print(f"\n=== PROJECT SCAN COMPLETE ===")
        print(f"Project: {project_name}")
        print(f"Collected {len(all_issue_urls)} issue URLs")
        print(f"Processed {len(processed_issues)} issues")
        print(f"Stored {stored_count} issues in database table '{table_name}'")
        print(f"Collection time: {collection_time:.1f} seconds")
        print(f"Processing time: {processing_time:.1f} seconds")

        collection_rate = len(all_issue_urls) / collection_time if collection_time > 0 else 0
        processing_rate = len(processed_issues) / processing_time if processing_time > 0 else 0
        print(f"Collection rate: {collection_rate:.1f} pages/sec")
        print(f"Processing rate: {processing_rate:.1f} issues/sec")

        return True

    except Exception as e:
        print(f"Error in fast project scanning process: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========= ▶ Entry Point ========= #
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fast_project_scanner.py <project_cookie_value> [max_pages]")
        print("Example: python fast_project_scanner.py 153 50")
        print("         python fast_project_scanner.py 153")
        sys.exit(1)

    project_cookie_value = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    success = scan_project_issues_fast(project_cookie_value, max_pages)

    if success:
        print("Fast project scanning completed successfully!")
    else:
        print("Fast project scanning failed!")
        sys.exit(1)