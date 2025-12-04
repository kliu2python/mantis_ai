#!/usr/bin/env python3
"""
Simple script to test cookies and verify project access
"""

import json
import os
from playwright.sync_api import sync_playwright

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

def test_project_access(project_id=None):
    """Test access to a specific project"""
    print("Testing Mantis access with current cookies...")

    # Load cookies
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

    # If a project ID is specified, modify the cookies
    if project_id:
        print(f"Setting project cookie to: {project_id}")
        if 'storage_state' in context_args:
            # Find and update MANTIS_PROJECT_COOKIE or add it
            cookies = context_args['storage_state']['cookies']
            project_cookie_found = False
            for cookie in cookies:
                if cookie.get('name') == 'MANTIS_PROJECT_COOKIE':
                    cookie['value'] = str(project_id)
                    project_cookie_found = True
                    break

            # If not found, add it
            if not project_cookie_found:
                cookies.append({
                    "name": "MANTIS_PROJECT_COOKIE",
                    "value": str(project_id),
                    "domain": ".mantis.fortinet.com",
                    "path": "/"
                })

    try:
        with sync_playwright() as p:
            # Run in headed mode to visually verify
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(**context_args)
            page = context.new_page()

            # Navigate to the main page
            test_url = MANTIS_BASE_URL
            if project_id:
                test_url += f"?project_id={project_id}"

            print(f"Navigating to: {test_url}")
            page.goto(test_url, timeout=30000)
            page.wait_for_load_state("networkidle")

            # Wait for user to observe
            print("Page loaded. Check the browser window to verify:")
            print("- Are you logged in?")
            print("- Is the correct project selected?")
            print("- Press ENTER to continue...")

            input()

            # Check current project
            project_selector = page.query_selector("select[name='project_id']")
            if project_selector:
                selected_option = project_selector.query_selector("option:checked")
                if selected_option:
                    project_text = selected_option.text_content().strip()
                    print(f"Current project: {project_text}")

                    # Check if it matches expected project
                    if project_id:
                        print(f"Expected project ID: {project_id}")

            # Check if we're on the right page
            current_url = page.url
            print(f"Current URL: {current_url}")

            page.close()
            browser.close()

            print("Test completed")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("Mantis Cookie Test Script")
    print("=" * 30)

    # First, let's see what cookies we have
    cookies_data = load_cookies()
    if cookies_data:
        project_cookies = []
        if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
            for cookie in cookies_data['cookies']:
                if 'project' in cookie.get('name', '').lower():
                    project_cookies.append(cookie)

        if project_cookies:
            print("Found project cookies:")
            for cookie in project_cookies:
                print(f"  {cookie['name']}: {cookie['value']}")
            print()

    # Ask user for project ID to test
    project_id = input("Enter project ID to test (or press ENTER to use current cookies): ").strip()
    if not project_id:
        project_id = None

    test_project_access(project_id)

if __name__ == "__main__":
    main()