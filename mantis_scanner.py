#!/usr/bin/env python3
"""
Enhanced Mantis Bug Tracker Scanner
Iterates through ALL pages of projects to find all issues
"""

import json
import os
import sqlite3
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from typing import List, Dict, Any

# ========= 🔧 CONFIG ========= #
MANTIS_BASE_URL = os.environ.get('MANTIS_BASE_URL', 'https://mantis.fortinet.com/')
COOKIE_FILE = "cookies.json"
SQLITE_DB_FILE = "mantis_data.db"

# ========= 🗄️ SQLite Database Integration ========= #
def init_database():
    """Initialize SQLite database with required tables"""
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        # Create projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                project_name TEXT,
                project_url TEXT,
                scanned_at TIMESTAMP
            )
        """)

        # Create issues table - simplified schema focusing on correct project info
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id TEXT,
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

def store_data_in_sqlite(table_name: str, data: List[Dict[str, Any]]) -> bool:
    """Store data in SQLite database"""
    if not data:
        print("No data to store")
        return True

    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cursor = conn.cursor()

        print(f"Attempting to store {len(data)} records in SQLite table '{table_name}'...")

        # Add timestamp to each record
        timestamp = datetime.now(timezone.utc)

        if table_name == "projects":
            for record in data:
                cursor.execute("""
                    INSERT INTO projects (project_id, project_name, project_url, scanned_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    record.get('project_id'),
                    record.get('project_name'),
                    record.get('project_url'),
                    timestamp
                ))
        elif table_name == "issues":
            for record in data:
                # Convert bugnotes to JSON string if it exists
                bugnotes_str = json.dumps(record.get('bugnotes', [])) if record.get('bugnotes') else None

                cursor.execute("""
                    INSERT INTO issues (
                        issue_id, project_id, project_name, url, category, summary, description,
                        steps_to_reproduce, additional_information, status, resolution,
                        reporter, assigned_to, priority, severity, date_submitted,
                        last_updated, version, fixed_in_version, target_version,
                        bugnotes, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get('issue_id'),
                    record.get('project_id'),
                    record.get('project_name'),
                    record.get('url'),
                    record.get('category'),
                    record.get('summary'),
                    record.get('description'),
                    record.get('steps_to_reproduce'),
                    record.get('additional_information'),
                    record.get('status'),
                    record.get('resolution'),
                    record.get('reporter'),
                    record.get('assigned_to'),
                    record.get('priority'),
                    record.get('severity'),
                    record.get('date_submitted'),
                    record.get('last_updated'),
                    record.get('version'),
                    record.get('fixed_in_version'),
                    record.get('target_version'),
                    bugnotes_str,
                    timestamp
                ))

        conn.commit()
        conn.close()
        print(f"Successfully stored {len(data)} records in SQLite table '{table_name}'")
        return True

    except Exception as e:
        print(f"Error storing data in SQLite: {e}")
        return False

# ========= 🔍 Project and Issue Scanning Logic ========= #
def get_project_list() -> List[Dict[str, str]]:
    """
    Extract list of projects from Mantis dashboard
    """
    projects = []

    # Load existing cookies for authentication, but filter out conflicting project cookie
    context_args = {}
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    # Filter out MANTIS_PROJECT_COOKIE to avoid conflicts with project_id parameter
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
            page = context.new_page()

            # Navigate to the main page
            page.goto(urljoin(MANTIS_BASE_URL, "view_all_bug_page.php?view_type=0"))
            page.wait_for_load_state("networkidle")

            # Find the project selector dropdown
            project_dropdown = page.query_selector("select[name='project_id']")
            if project_dropdown:
                options = page.query_selector_all("select[name='project_id'] option")
                for option in options:
                    project_id = option.get_attribute("value")
                    project_name = option.text_content().strip()
                    # Skip the "All Projects" option (usually value="0")
                    if project_id and project_id != "0" and project_name:
                        project_url = urljoin(MANTIS_BASE_URL, f"view_all_bug_page.php?project_id={project_id}")
                        projects.append({
                            "id": project_id,
                            "name": project_name,
                            "url": project_url
                        })

            browser.close()

    except Exception as e:
        print(f"Error getting project list: {e}")

    return projects

def get_total_pages_for_project(context, project_id: str) -> int:
    """
    Determine the total number of pages for a project by checking the actual navigation

    For large projects like FortiOS, we can't check every page, so we:
    1. Load the first page to get the navigation controls
    2. Parse the maximum page number from the navigation links
    3. This is much more efficient than sampling hundreds/thousands of pages
    """
    try:
        print(f"Project {project_id}: Determining total pages from navigation")

        # Create a temporary page for checking
        temp_page = context.new_page()

        # Navigate to the first page of the project
        project_url = f"https://mantis.fortinet.com/view_all_bug_page.php?project_id={project_id}"
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
                print(f"Project {project_id}: Found {max_page} pages from navigation links")
                temp_page.close()
                return max_page

        temp_page.close()
        print(f"Project {project_id}: Defaulting to 1 page - no pagination info found")
        return 1  # Default to 1 page if we can't determine

    except Exception as e:
        print(f"Error determining total pages for project {project_id}: {e}")
        return 1  # Default to 1 page if we can't determine

def _count_issues_on_page(page_obj, project_id: str, page_number: int) -> int:
    """
    Count actual issues on a specific page (helper function)
    """
    # Navigate to the specific page
    if page_number == 1:
        project_url = f"https://mantis.fortinet.com/view_all_bug_page.php?project_id={project_id}"
    else:
        project_url = f"https://mantis.fortinet.com/view_all_bug_page.php?project_id={project_id}&page_number={page_number}"

    try:
        page_obj.goto(project_url)
        page_obj.wait_for_load_state("networkidle")
        page_obj.wait_for_timeout(200)  # Shorter timeout for checking

        # Find the main bug list table
        tables = page_obj.query_selector_all("table")

        if len(tables) >= 4:
            bug_table = tables[3]  # Table 4 (0-indexed)
            rows = bug_table.query_selector_all("tr")

            # Count valid issue IDs
            issue_count = 0
            for i, row in enumerate(rows):
                cells = row.query_selector_all("td")
                if len(cells) >= 2:
                    issue_id = cells[1].text_content().strip()
                    if issue_id and issue_id.isdigit():
                        issue_count += 1

            return issue_count
        else:
            return 0

    except Exception as e:
        print(f"Error checking page {page_number}: {e}")
        return 0

def get_issue_urls_from_project_page(page, project_id: str, page_number: int) -> List[Dict[str, str]]:
    """
    Extract issue URLs from a specific page of a project
    """
    issue_urls = []

    try:
        # Navigate to the specific page if it's not page 1
        if page_number > 1:
            page_url = f"https://mantis.fortinet.com/view_all_bug_page.php?project_id={project_id}&page_number={page_number}&view_type=0"
            print(f"  Navigating to page {page_number}: {page_url}")
            page.goto(page_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)

        # Find the main bug list table
        tables = page.query_selector_all("table")

        if len(tables) >= 4:
            bug_table = tables[3]  # Table 4 (0-indexed)
            rows = bug_table.query_selector_all("tr")

            # Extract issue URLs (starting from row 2)
            for i in range(2, len(rows)):
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
                            issue_urls.append({
                                "issue_id": issue_id,
                                "url": urljoin(MANTIS_BASE_URL, issue_url)
                            })

        print(f"  Page {page_number}: Found {len(issue_urls)} issues")

    except Exception as e:
        print(f"Error getting issue URLs from project {project_id} page {page_number}: {e}")

    return issue_urls

def get_all_issue_urls_from_project(project_id: str, project_name: str) -> List[Dict[str, str]]:
    """
    Extract ALL issue URLs from a project by iterating through all pages
    """
    print(f"Getting ALL issue URLs for project {project_name} (ID: {project_id})")

    all_issue_urls = []

    # Load existing cookies for authentication, but filter out conflicting project cookie
    context_args = {}
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    # Filter out MANTIS_PROJECT_COOKIE to avoid conflicts with project_id parameter
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
            page = context.new_page()

            # Navigate to the first page of the project
            project_url = f"https://mantis.fortinet.com/view_all_bug_page.php?project_id={project_id}"
            print(f"  Navigating to first page: {project_url}")
            page.goto(project_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)

            # Determine total number of pages by actually checking content
            total_pages = get_total_pages_for_project(context, project_id)
            print(f"  Project {project_name} has {total_pages} pages with actual content")

            # Process first page (already loaded)
            first_page_issues = get_issue_urls_from_project_page(page, project_id, 1)
            all_issue_urls.extend(first_page_issues)

            # Process remaining pages
            for page_num in range(2, total_pages + 1):
                print(f"  Processing page {page_num}/{total_pages}")
                page_issues = get_issue_urls_from_project_page(page, project_id, page_num)
                all_issue_urls.extend(page_issues)

                # Add a small delay to be respectful to the server
                page.wait_for_timeout(200)

            browser.close()

    except Exception as e:
        print(f"Error getting all issue URLs from project {project_name}: {e}")

    print(f"  Total issues found for {project_name}: {len(all_issue_urls)}")
    return all_issue_urls

def extract_complete_issue_details(issue_info: Dict[str, str]) -> Dict[str, Any]:
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

    # Load existing cookies for authentication, but filter out conflicting project cookie
    context_args = {}
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    # Filter out MANTIS_PROJECT_COOKIE to avoid conflicts with project_id parameter
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

    # Use a separate function to avoid nested Playwright contexts
    try:
        issue_data.update(_extract_issue_details_with_context(context_args, issue_url))
    except Exception as e:
        print(f"Error extracting issue details for {issue_url}: {e}")

    return issue_data

def _extract_issue_details_with_context(context_args: Dict, issue_url: str) -> Dict[str, Any]:
    """
    Helper function to extract issue details using a separate Playwright context
    """
    from playwright.sync_api import sync_playwright

    issue_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**context_args)
        page = context.new_page()

        # Navigate to the issue page
        page.goto(issue_url)
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(500)

        # Extract information using targeted selectors
        # Find tables that contain issue information
        tables = page.query_selector_all("table")

        # Process tables looking for issue data
        for table in tables:
            rows = table.query_selector_all("tr")

            # Process each row looking for label/value pairs
            for i, row in enumerate(rows):
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
                        if i + 1 < len(rows):
                            next_row = rows[i + 1]
                            next_cells = next_row.query_selector_all("td, th")
                            if len(next_cells) >= 2:
                                # The category value is in the second cell of the next row
                                category_value = next_cells[1].text_content().strip()
                                if category_value:
                                    issue_data['category'] = category_value
                                    print(f"DEBUG: Found category '{category_value}' in table, row {i+1}")

        # Extract project information from category
        # The category field typically contains project information in format like:
        # "[ProjectName] SubCategory" or just "ProjectName"
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
                # Use category as project name if no brackets
                # But we need to map this to actual project IDs
                project_name = category.split()[0] if category.split() else category
                issue_data['project_name'] = project_name

        # Extract bugnotes specifically
        bugnotes = []
        bugnotes_section = page.query_selector("#bugnotes, .bugnotes")

        if bugnotes_section:
            bugnote_elements = bugnotes_section.query_selector_all(".bugnote")

            for bugnote_element in bugnote_elements:
                bugnote_data = {}

                # Try different approaches to extract bugnote data
                # Author - look for text with parentheses (like "Name (username)")
                author_candidates = bugnote_element.query_selector_all("*")
                for candidate in author_candidates:
                    text = candidate.text_content().strip()
                    if '(' in text and ')' in text and len(text) > 5:
                        bugnote_data["author"] = text
                        break

                # Date - look for text with colon or dash
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
                content_candidates = bugnote_element.query_selector_all("p, div, span")
                for candidate in content_candidates:
                    text = candidate.text_content().strip()
                    # Only save substantial content, avoid buttons/controls
                    if len(text) > 15 and '[' not in text and ']' not in text:
                        # Check if it's not just navigation/control text
                        if not any(skip_word in text.lower() for skip_word in ['reply', 'edit', 'delete', 'quote']):
                            bugnote_data["content"] = text
                            break

                if bugnote_data:
                    bugnotes.append(bugnote_data)

            if bugnotes:
                issue_data["bugnotes"] = bugnotes

        page.close()
        browser.close()

    return issue_data

def get_project_id_by_name(project_name: str) -> str:
    """
    Map project name to project ID using the project list
    """
    try:
        # Read project list from file
        with open('project_list.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Search for project in the list
        for line in lines:
            if project_name.lower() in line.lower():
                # Extract project ID from line like "51. ID: 146 - Name: FortiIdentity Cloud"
                parts = line.split()
                if 'ID:' in parts:
                    id_index = parts.index('ID:') + 1
                    if id_index < len(parts):
                        return parts[id_index].rstrip(',')

        # If we can't find exact match, try partial matching
        for line in lines:
            if project_name.lower() in line.lower():
                # Extract the ID part
                import re
                match = re.search(r'ID:\s*(\d+)', line)
                if match:
                    return match.group(1)

    except Exception as e:
        print(f"Error mapping project name to ID: {e}")

    return ""  # Return empty string if not found

def process_issues_batch(issue_urls: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Process a batch of issues and extract their details
    """
    all_issues_data = []

    for i, issue_info in enumerate(issue_urls, 1):
        issue_url = issue_info.get("url")
        if issue_url:
            print(f"Processing issue {i}/{len(issue_urls)}: {issue_url}")

            # Click into each issue and extract detailed information
            detailed_issue = extract_complete_issue_details(issue_info)

            # Extract project information from category and map to project ID
            project_name = detailed_issue.get('project_name', '')
            if project_name:
                project_id = get_project_id_by_name(project_name)
                detailed_issue['project_id'] = project_id
                detailed_issue['project_name'] = project_name
            else:
                # Fallback - if no project info found, mark as unknown
                detailed_issue['project_id'] = ''
                detailed_issue['project_name'] = 'Unknown'

            all_issues_data.append(detailed_issue)

    return all_issues_data

def scan_enhanced_mantis_data():
    """
    Main function to scan all Mantis projects with pagination support
    """
    print("Starting ENHANCED Mantis scanner with pagination support...")

    # Initialize database
    if not init_database():
        print("Failed to initialize database")
        return False

    # Get list of all projects
    projects = get_project_list()

    if not projects:
        print("No projects found!")
        return False

    print(f"Found {len(projects)} projects.")

    # Store project data
    store_data_in_sqlite("projects", projects)

    # Process all projects to get ALL issue URLs (including all pages)
    all_issue_urls = []
    for i, project in enumerate(projects, 1):
        print(f"\n[{i}/{len(projects)}] Getting ALL issue URLs for project: {project.get('name')}")
        issue_urls = get_all_issue_urls_from_project(project.get("id"), project.get("name"))
        all_issue_urls.extend(issue_urls)
        print(f"  Running total: {len(all_issue_urls)} issues from all projects")

    if not all_issue_urls:
        print("No issues found!")
        return False

    print(f"\nTOTAL ISSUES TO PROCESS: {len(all_issue_urls)}")

    # Process all issues and extract detailed information
    all_issues_data = process_issues_batch(all_issue_urls)

    # Store issues data
    if all_issues_data:
        store_data_in_sqlite("issues", all_issues_data)
        print(f"\nSuccessfully processed {len(all_issues_data)} issues")
    else:
        print("\nNo issue data to store")

    print(f"\n=== ENHANCED SCAN COMPLETE ===")
    print(f"Processed {len(all_issue_urls)} issues from all project pages")
    print("Project information correctly extracted from Category field")

    return True

# ========= ▶ Entry Point ========= #
if __name__ == "__main__":
    scan_enhanced_mantis_data()