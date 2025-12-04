#!/usr/bin/env python3
"""
Script to list all available projects in Mantis
"""

import json
import os
from playwright.sync_api import sync_playwright
import time

MANTIS_BASE_URL = os.environ.get('MANTIS_BASE_URL', 'https://mantis.fortinet.com/')
COOKIE_FILE = "cookies.json"

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

def list_all_projects():
    """List all available projects in Mantis"""
    print("Loading cookies...")
    cookies_data = load_cookies()
    if not cookies_data:
        print("Cannot load cookies, exiting")
        return

    # Prepare context arguments
    context_args = {}
    if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
        context_args['storage_state'] = {
            "cookies": cookies_data['cookies'],
            "origins": cookies_data.get("origins", [])
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the main page
            print("Navigating to Mantis...")
            page.goto(MANTIS_BASE_URL, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)  # Wait for page to fully load

            # Look for project selector
            print("Looking for project selector...")
            project_selector = page.query_selector("select[name='project_id']")

            if project_selector:
                print("\n=== AVAILABLE PROJECTS ===")
                options = project_selector.query_selector_all("option")

                projects = []
                for option in options:
                    project_id = option.get_attribute("value")
                    project_name = option.text_content().strip()

                    # Skip empty options
                    if project_id and project_name:
                        projects.append((project_id, project_name))
                        print(f"{project_id}: {project_name}")

                print(f"\nFound {len(projects)} projects")

                # Save to file for reference
                with open("project_list.txt", "w") as f:
                    f.write("# Mantis Project List\n")
                    f.write("# Format: project_id: project_name\n\n")
                    for project_id, project_name in projects:
                        f.write(f"{project_id}: {project_name}\n")

                print("\nProject list saved to project_list.txt")

            else:
                print("Project selector not found on page")

                # Try to find any project-related elements
                print("Searching for project-related elements...")
                project_elements = page.query_selector_all("[class*='project'], [id*='project'], select")

                for element in project_elements:
                    tag_name = element.evaluate("el => el.tagName").lower()
                    if tag_name in ['select', 'option']:
                        text = element.text_content().strip()
                        if text:
                            print(f"Found element: {tag_name} - {text[:50]}")

            page.close()
            browser.close()

    except Exception as e:
        print(f"Error listing projects: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("Mantis Project Listing Script")
    print("=" * 40)
    list_all_projects()

if __name__ == "__main__":
    main()