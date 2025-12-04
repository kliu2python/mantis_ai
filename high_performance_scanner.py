#!/usr/bin/env python3
"""
High-Performance Mantis Scanner
Processes ALL issues from All Projects view with maximum speed optimization
Uses multiprocessing for both page collection and issue processing
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from typing import List, Dict, Any
import multiprocessing as mp
import threading
import queue
import time
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import math

# ========= 🔧 CONFIG ========= #
MANTIS_BASE_URL = os.environ.get('MANTIS_BASE_URL', 'https://mantis.fortinet.com/')
COOKIE_FILE = "cookies.json"
SQLITE_DB_FILE = "mantis_data.db"

# Performance configuration - HIGH SPEED SETTINGS
PAGE_WORKERS = 10  # Number of concurrent workers for page collection
ISSUE_WORKERS = 30  # Number of concurrent workers for issue processing
PAGES_PER_BATCH = 100  # Process pages in batches
DB_COMMIT_BATCH_SIZE = 500  # Larger batch size for database commits

# Rate limiting configuration - OPTIMIZED FOR SPEED
REQUEST_DELAY = 0.1  # Minimal delay between requests
MAX_RETRIES = 2  # Fewer retries for speed

# Target: 170K issues in 10 hours = 4.7 issues/sec minimum
# With 30 workers, we should achieve 10+ issues/sec

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

# ========= 🔍 Page Collection Logic (Multiprocessing) ========= #
def get_issue_urls_from_page_worker(page_number: int, context_args: Dict) -> List[Dict[str, str]]:
    """
    Worker function to extract issue URLs from a specific page
    Runs in a separate Playwright context
    """
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
            page.wait_for_timeout(100)  # Minimal wait

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

def collect_all_issue_urls_parallel(total_pages: int, context_args: Dict) -> List[Dict[str, str]]:
    """
    Collect all issue URLs from all pages using multiprocessing
    Processes pages in batches to manage memory and connections
    """
    print(f"Collecting issue URLs from all {total_pages} pages using {PAGE_WORKERS} workers...")

    all_issue_urls = []

    # Process pages in batches
    batch_size = PAGE_WORKERS * 5  # Process 50 pages per batch
    total_batches = math.ceil(total_pages / batch_size)

    print(f"Processing {total_pages} pages in {total_batches} batches of {batch_size} pages each")

    for batch_num in range(total_batches):
        start_page = batch_num * batch_size + 1
        end_page = min((batch_num + 1) * batch_size, total_pages)

        print(f"Processing batch {batch_num + 1}/{total_batches}: pages {start_page}-{end_page}")

        # Create page numbers for this batch
        page_numbers = list(range(start_page, end_page + 1))

        # Use ThreadPoolExecutor for concurrent page processing
        with ThreadPoolExecutor(max_workers=PAGE_WORKERS) as executor:
            # Submit all page processing tasks
            future_to_page = {
                executor.submit(get_issue_urls_from_page_worker, page_num, context_args): page_num
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

    print(f"Collected {len(all_issue_urls)} issue URLs from {total_pages} pages")
    return all_issue_urls

# ========= 🔍 Issue Processing Logic ========= #
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
            # Add minimal rate limiting delay
            time.sleep(REQUEST_DELAY)

            issue_data.update(_extract_issue_details_with_context(context_args, issue_url))
            return issue_data
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {issue_url}: {e}")
            if attempt < MAX_RETRIES - 1:
                # Minimal backoff
                time.sleep(REQUEST_DELAY * 2)
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
            # print(f"    Extracting details from: {issue_url}")
            page.goto(issue_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(100)  # Minimal wait

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
        return {}

    return issue_data

# ========= 🚀 High-Performance Issue Processing Functions ========= #
class HighPerformanceIssueProcessor:
    def __init__(self, max_workers=ISSUE_WORKERS):
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.results_collector = None
        self.shutdown_event = threading.Event()
        self.start_time = time.time()
        self.processed_count = 0

    def start_workers(self):
        """Start worker threads"""
        print(f"Starting {self.max_workers} worker threads for issue processing...")

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
                # print(f"Worker {worker_id} processing issue {issue_info.get('issue_id')}")

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

        # Start collecting results in a separate thread
        def collector():
            while not self.shutdown_event.is_set():
                try:
                    result = self.result_queue.get(timeout=1)
                    if result:
                        results.append(result)
                        self.processed_count += 1

                        # Calculate and display performance metrics
                        elapsed_time = time.time() - self.start_time
                        rate = self.processed_count / elapsed_time if elapsed_time > 0 else 0

                        print(f"Processed {self.processed_count} issues ({rate:.1f} issues/sec)")

                        # Process results in batches
                        if batch_callback and len(results) >= DB_COMMIT_BATCH_SIZE:
                            try:
                                batch_callback(results)
                            except Exception as e:
                                print(f"Error in batch callback: {e}")
                            results.clear()

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
        print(f"Starting high-performance processing with {self.max_workers} workers for {len(issue_urls)} issues")
        self.start_time = time.time()
        self.processed_count = 0

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
    Main function to scan ALL Mantis issues from All Projects view using high-performance processing
    """
    print("Starting High-Performance Mantis scanner...")
    print("Project information will be extracted from each issue's Category field")
    print(f"Using {PAGE_WORKERS} concurrent workers for page collection")
    print(f"Using {ISSUE_WORKERS} concurrent workers for issue processing")
    print(f"Target: Process 170K issues in 10 hours (4.7 issues/sec minimum)")

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
        # We know there are 3709 pages, so we don't need to determine this dynamically
        total_pages = 3709
        print(f"Using known total of {total_pages} pages in All Projects view")

        # Collect all issue URLs using multiprocessing
        print(f"\n=== PHASE 1: Collecting issue URLs from all {total_pages} pages ===")
        start_time = time.time()
        all_issue_urls = collect_all_issue_urls_parallel(total_pages, context_args)
        collection_time = time.time() - start_time

        print(f"\nCollected {len(all_issue_urls)} issue URLs in {collection_time:.1f} seconds")
        print(f"Collection rate: {len(all_issue_urls)/collection_time:.1f} pages/sec")

        # For your specific requirement: process only 170K issues
        target_issues = max(170000, len(all_issue_urls))
        if len(all_issue_urls) > target_issues:
            print(f"\nLimiting to {target_issues} issues as requested")
            all_issue_urls = all_issue_urls[:target_issues]

        # Create high-performance issue processor
        processor = HighPerformanceIssueProcessor(max_workers=ISSUE_WORKERS)

        # Define batch callback for storing results
        def store_batch(results):
            if results:
                print(f"Storing batch of {len(results)} issues to database")
                try:
                    store_issues_data_batch(results)
                except Exception as e:
                    print(f"Error storing batch: {e}")

        # Process issues using high-performance processing
        print(f"\n=== PHASE 2: Extracting detailed information from {len(all_issue_urls)} issues ===")
        start_time = time.time()
        all_issues_data = processor.process_issues(all_issue_urls, store_batch)
        processing_time = time.time() - start_time

        print(f"\n=== SCAN COMPLETE ===")
        print(f"Processed {len(all_issue_urls)} issues in {processing_time:.1f} seconds")
        rate = len(all_issue_urls) / processing_time if processing_time > 0 else 0
        print(f"Processing rate: {rate:.1f} issues/sec")
        print("Project information correctly extracted from Category field")
        print(f"Data stored in {SQLITE_DB_FILE}")

        # Performance assessment
        target_rate = 4.7  # issues per second for 170K in 10 hours
        if rate >= target_rate:
            print(f"✅ PERFORMANCE TARGET MET: {rate:.1f} issues/sec >= {target_rate} issues/sec")
        else:
            print(f"❌ Performance target missed: {rate:.1f} issues/sec < {target_rate} issues/sec")

        # Time estimation for 170K issues
        estimated_time_hours = (170000 / rate) / 3600 if rate > 0 else 0
        print(f"Estimated time for 170K issues: {estimated_time_hours:.1f} hours")

        return True

    except Exception as e:
        print(f"Error in main scanning process: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========= ▶ Entry Point ========= #
if __name__ == "__main__":
    scan_all_mantis_issues()