#!/usr/bin/env python3
"""
Optimized Mantis Scanner that processes ALL issues from All Projects view
Gets project information from each issue's Category field
Uses optimized threading and batch processing for faster performance
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from typing import List, Dict, Any
import threading
import queue
import time
import signal
import sys

# ========= 🔧 CONFIG ========= #
MANTIS_BASE_URL = os.environ.get('MANTIS_BASE_URL', 'https://mantis.fortinet.com/')
COOKIE_FILE = "cookies.json"
SQLITE_DB_FILE = "mantis_data.db"

# Performance configuration
MAX_WORKERS = 10  # Number of concurrent workers
BATCH_SIZE = 100  # Number of issues to collect before processing
DB_COMMIT_BATCH_SIZE = 100  # Number of records to commit to DB at once
WORKER_TIMEOUT = 30  # Timeout for worker threads in seconds

# Rate limiting configuration
REQUEST_DELAY = 0.5  # Delay between requests in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests

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
        return False

# ========= 🔍 Issue Scanning Logic ========= #
def get_total_pages_for_all_projects(context) -> int:
    """
    Determine total pages from All Projects view (most efficient approach)
    """
    try:
        print("Determining total pages from All Projects view")

        # Create a temporary page for checking
        temp_page = context.new_page()

        # Navigate to All Projects view (no project_id parameter)
        project_url = f"{MANTIS_BASE_URL}view_all_bug_page.php"
        temp_page.goto(project_url)
        temp_page.wait_for_load_state("networkidle")
        temp_page.wait_for_timeout(500)

        # Look for page navigation links and find the highest page number
        page_links = temp_page.query_selector_all("a[href*='page_number']")

        if page_links:
            max_page = 1
            for link in page_links:
                href = link.get_attribute("href")
                if href:
                    # Extract page_number parameter
                    import urllib.parse
                    parsed = urllib.parse.urlparse(href)
                    params = urllib.parse.parse_qs(parsed.query)
                    if 'page_number' in params:
                        page_num = int(params['page_number'][0])
                        max_page = max(max_page, page_num)

            if max_page > 1:
                print(f"Found {max_page} pages from All Projects navigation links")
                temp_page.close()
                return max_page

        temp_page.close()
        print("Defaulting to 1 page - no pagination info found")
        return 1

    except Exception as e:
        print(f"Error determining total pages: {e}")
        return 1

def get_issue_urls_from_page(page, page_number: int) -> List[Dict[str, str]]:
    """
    Extract issue URLs from a specific page of All Projects view
    """
    issue_urls = []

    try:
        # Navigate to the specific page if it's not page 1
        if page_number > 1:
            page_url = f"{MANTIS_BASE_URL}view_all_bug_page.php?page_number={page_number}"
            print(f"  Navigating to page {page_number}: {page_url}")
            page.goto(page_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)

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

        print(f"  Page {page_number}: Found {len(issue_urls)} issues")

    except Exception as e:
        print(f"Error getting issue URLs from page {page_number}: {e}")

    return issue_urls

def extract_complete_issue_details(issue_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Click into an issue and extract complete detailed information
    Gets the CORRECT project information from the Category field
    Implements rate limiting and error handling with retries
    """
    issue_url = issue_info.get("url")
    if not issue_url:
        return {}

    issue_data = {
        "url": issue_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_info.get("issue_id")
    }

    # Load existing cookies for authentication, but filter out conflicting project cookie
    context_args = {}
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    # Filter out MANTIS_PROJECT_COOKIE to avoid conflicts
                    filtered_cookies = []
                    for cookie in cookies_data['cookies']:
                        if cookie.get('name') != 'MANTIS_PROJECT_COOKIE':
                            filtered_cookies.append(cookie)

                    context_args['storage_state'] = {
                        "cookies": filtered_cookies,
                        "origins": cookies_data.get("origins", [])
                    }
        except Exception as e:
            print(f"Could not load cookies: {e}")

    # Implement retry mechanism
    for attempt in range(MAX_RETRIES):
        try:
            # Add rate limiting delay
            time.sleep(REQUEST_DELAY)

            issue_data.update(_extract_issue_details_with_context(context_args, issue_url))
            return issue_data
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {issue_url}: {e}")
            if attempt < MAX_RETRIES - 1:
                # Exponential backoff
                wait_time = (2 ** attempt) + REQUEST_DELAY
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed to extract issue details for {issue_url} after {MAX_RETRIES} attempts")
                # Fallback to returning basic issue data
                return issue_data

    return issue_data

def _extract_issue_details_with_context(context_args: Dict, issue_url: str) -> Dict[str, Any]:
    """
    Helper function to extract issue details using a separate Playwright context
    Implements better error handling and timeout management
    """
    issue_data = {}

    try:
        # Import playwright inside the function to avoid context issues
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the issue page with timeout handling
            print(f"    Extracting details from: {issue_url}")
            try:
                page.goto(issue_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=30000)
                page.wait_for_timeout(500)
            except Exception as e:
                print(f"    Timeout or error loading page {issue_url}: {e}")
                page.close()
                browser.close()
                return {}

            # Extract information using targeted selectors
            # Find tables that contain issue information
            try:
                tables = page.query_selector_all("table")
            except Exception as e:
                print(f"    Error querying tables: {e}")
                page.close()
                browser.close()
                return {}

            # Process tables looking for issue data
            for table in tables:
                try:
                    rows = table.query_selector_all("tr")
                except Exception as e:
                    print(f"    Error querying rows: {e}")
                    continue

                # Process each row looking for label/value pairs
                for row in rows:
                    try:
                        cells = row.query_selector_all("td, th")
                    except Exception as e:
                        print(f"    Error querying cells: {e}")
                        continue

                    # Look for rows with 2+ cells where first might be a label
                    if len(cells) >= 2:
                        try:
                            first_cell_text = cells[0].text_content().strip().lower()
                            second_cell_text = cells[1].text_content().strip()
                        except Exception as e:
                            print(f"    Error extracting cell text: {e}")
                            continue

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
                            try:
                                next_row = row.query_selector("~ tr")  # Next sibling tr
                                if next_row:
                                    next_cells = next_row.query_selector_all("td, th")
                                    if len(next_cells) >= 2:
                                        # The category value is in the second cell of the next row
                                        category_value = next_cells[1].text_content().strip()
                                        if category_value:
                                            issue_data['category'] = category_value
                            except Exception as e:
                                print(f"    Error extracting category from special handling: {e}")
                                continue

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
            try:
                bugnotes_section = page.query_selector("#bugnotes, .bugnotes")
            except Exception as e:
                print(f"    Error querying bugnotes section: {e}")
                bugnotes_section = None

            if bugnotes_section:
                try:
                    bugnote_elements = bugnotes_section.query_selector_all(".bugnote")
                except Exception as e:
                    print(f"    Error querying bugnote elements: {e}")
                    bugnote_elements = []

                for bugnote_element in bugnote_elements:
                    bugnote_data = {}

                    # Try to extract bugnote information
                    # Author - look for text with parentheses
                    try:
                        author_element = bugnote_element.query_selector(".bugnoteheader")
                        if author_element:
                            author_text = author_element.text_content().strip()
                            bugnote_data["author"] = author_text
                    except Exception as e:
                        print(f"    Error extracting author: {e}")

                    # Date - look for date information
                    try:
                        date_candidates = bugnote_element.query_selector_all("*")
                        for candidate in date_candidates:
                            text = candidate.text_content().strip()
                            # Look for date-like patterns
                            if (':' in text and len(text) > 10) or ('-' in text and len(text) > 8):
                                # Additional check to avoid button text
                                if '[' not in text and ']' not in text:
                                    bugnote_data["date"] = text
                                    break
                    except Exception as e:
                        print(f"    Error extracting date: {e}")

                    # Content - look for substantial text
                    try:
                        content_element = bugnote_element.query_selector(".bugnote-note")
                        if content_element:
                            content_text = content_element.text_content().strip()
                            if len(content_text) > 5:
                                bugnote_data["content"] = content_text
                    except Exception as e:
                        print(f"    Error extracting content: {e}")

                    if bugnote_data:
                        bugnotes.append(bugnote_data)

                if bugnotes:
                    issue_data["bugnotes"] = bugnotes

            page.close()
            browser.close()

    except Exception as e:
        print(f"Error extracting issue details: {e}")
        return {}

    return issue_data

# ========= 🚀 Optimized Processing Functions ========= #
class IssueProcessor:
    def __init__(self, max_workers=MAX_WORKERS):
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.results_collector = None
        self.shutdown_event = threading.Event()

    def start_workers(self):
        """Start worker threads"""
        print(f"Starting {self.max_workers} worker threads...")

        for i in range(self.max_workers):
            worker = threading.Thread(target=self.worker_thread, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

    def worker_thread(self, worker_id):
        """
        Worker thread function that processes issues from the task queue
        Implements better error handling and graceful shutdown
        """
        print(f"Worker {worker_id} started")

        while not self.shutdown_event.is_set():
            try:
                # Get a task from the queue (with timeout to allow graceful shutdown)
                issue_info = self.task_queue.get(timeout=1)

                # Process the task
                print(f"Worker {worker_id} processing issue {issue_info.get('issue_id')}")

                # Extract issue details
                detailed_issue = extract_complete_issue_details(issue_info)

                # Put result in result queue
                self.result_queue.put(detailed_issue)
                self.task_queue.task_done()

            except queue.Empty:
                # Timeout occurred, continue to check for shutdown signal
                continue
            except Exception as e:
                print(f"Worker {worker_id} encountered error: {e}")
                self.task_queue.task_done()
                # Even on error, we should continue processing other tasks
                continue

        print(f"Worker {worker_id} finished")

    def collect_results(self, batch_callback=None):
        """
        Collect results from worker threads and process them in batches
        Implements better error handling for result collection
        """
        results = []
        processed_count = 0

        # Start collecting results in a separate thread
        def collector():
            nonlocal results, processed_count
            while not self.shutdown_event.is_set():
                try:
                    result = self.result_queue.get(timeout=1)
                    if result:
                        results.append(result)
                        processed_count += 1
                        print(f"Processed {processed_count} issues")

                        # Process results in batches
                        if batch_callback and len(results) >= DB_COMMIT_BATCH_SIZE:
                            try:
                                batch_callback(results)
                            except Exception as e:
                                print(f"Error in batch callback: {e}")
                            results = []

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Error in collector thread: {e}")
                    continue

        self.results_collector = threading.Thread(target=collector)
        self.results_collector.daemon = True
        self.results_collector.start()

        return results

    def stop_workers(self):
        """Stop all worker threads gracefully"""
        print("Stopping worker threads...")
        self.shutdown_event.set()

        # Wait for all workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        # Wait for collector to finish
        if self.results_collector:
            self.results_collector.join(timeout=5)

    def process_issues(self, issue_urls: List[Dict[str, str]], batch_callback=None) -> List[Dict[str, Any]]:
        """
        Process issues using multiple worker threads with batch processing
        Implements better error handling and graceful shutdown
        """
        print(f"Starting optimized processing with {self.max_workers} workers for {len(issue_urls)} issues")

        # Start workers
        self.start_workers()

        # Add all tasks to the task queue
        for issue_info in issue_urls:
            self.task_queue.put(issue_info)

        # Start collecting results
        results = self.collect_results(batch_callback)

        try:
            # Wait for all tasks to be processed
            self.task_queue.join()
        except KeyboardInterrupt:
            print("Interrupted by user")
            self.shutdown_event.set()  # Signal shutdown to workers
        except Exception as e:
            print(f"Error while waiting for tasks to complete: {e}")
            self.shutdown_event.set()  # Signal shutdown to workers
        finally:
            self.stop_workers()

        return results

def scan_all_mantis_issues():
    """
    Main function to scan ALL Mantis issues from All Projects view using optimized processing
    Implements better error handling and graceful shutdown
    """
    print("Starting Optimized Mantis scanner with All Projects approach...")
    print("Project information will be extracted from each issue's Category field")
    print(f"Using {MAX_WORKERS} concurrent workers for faster processing")

    # Initialize database
    if not init_database():
        print("Failed to initialize database")
        return False

    # Load existing cookies for authentication, but filter out conflicting project cookie
    context_args = {}
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    # Filter out MANTIS_PROJECT_COOKIE to avoid conflicts
                    filtered_cookies = []
                    for cookie in cookies_data['cookies']:
                        if cookie.get('name') != 'MANTIS_PROJECT_COOKIE':
                            filtered_cookies.append(cookie)

                    context_args['storage_state'] = {
                        "cookies": filtered_cookies,
                        "origins": cookies_data.get("origins", [])
                    }
        except Exception as e:
            print(f"Could not load cookies: {e}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(**context_args)

            # Determine total number of pages from All Projects view
            total_pages = get_total_pages_for_all_projects(context)
            print(f"Found {total_pages} pages in All Projects view")

            # For a full scan, we would process all pages, but for testing we'll limit it
            pages_to_process = max(100, total_pages)  # Process first 100 pages or all if less
            print(f"Processing first {pages_to_process} pages...")

            all_issue_urls = []
            page = context.new_page()

            # Process pages with error handling
            try:
                for page_num in range(1, pages_to_process + 1):
                    print(f"\n--- Processing page {page_num}/{pages_to_process} ---")
                    page_issues = get_issue_urls_from_page(page, page_num)
                    all_issue_urls.extend(page_issues)
            except Exception as e:
                print(f"Error processing pages: {e}")
            finally:
                page.close()
                browser.close()

            print(f"\nCollected {len(all_issue_urls)} issue URLs from {pages_to_process} pages")

            # Create issue processor
            processor = IssueProcessor(max_workers=MAX_WORKERS)

            # Define batch callback for storing results
            def store_batch(results):
                if results:
                    print(f"Storing batch of {len(results)} issues to database")
                    try:
                        store_issues_data_batch(results)
                    except Exception as e:
                        print(f"Error storing batch: {e}")

            # Process issues using optimized processing
            print(f"\nExtracting detailed information from {len(all_issue_urls)} issues using optimized processing...")
            all_issues_data = processor.process_issues(all_issue_urls, store_batch)

            print(f"\n=== SCAN COMPLETE ===")
            print(f"Processed {len(all_issue_urls)} issues from {pages_to_process} pages")
            print("Project information correctly extracted from Category field")
            print(f"Data stored in {SQLITE_DB_FILE}")

            return True

    except Exception as e:
        print(f"Error in main scanning process: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========= ▶ Entry Point ========= #
if __name__ == "__main__":
    scan_all_mantis_issues()