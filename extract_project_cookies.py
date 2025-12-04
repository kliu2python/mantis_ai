#!/usr/bin/env python3
"""
Script to extract and display project cookies from cookies.json
"""

import json
import os

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

def extract_project_cookies(cookies_data):
    """Extract project-related cookies"""
    if not cookies_data or not isinstance(cookies_data, dict):
        return {}

    project_cookies = {}

    # Check if cookies are in storage_state format
    if 'cookies' in cookies_data:
        cookies = cookies_data['cookies']
    else:
        # Direct cookies array
        cookies = cookies_data if isinstance(cookies_data, list) else []

    # Look for project-related cookies
    for cookie in cookies:
        name = cookie.get('name', '')
        value = cookie.get('value', '')

        # Look for project cookies
        if 'project' in name.lower() or 'MANTIS_PROJECT_COOKIE' == name:
            project_cookies[name] = value
            print(f"Project Cookie Found: {name} = {value}")

        # Look for other potentially useful cookies
        elif any(keyword in name.lower() for keyword in ['session', 'auth', 'login']):
            print(f"Auth Cookie Found: {name} = {value}")

    return project_cookies

def display_all_cookies(cookies_data):
    """Display all cookies for inspection"""
    if not cookies_data or not isinstance(cookies_data, dict):
        print("No valid cookies data found")
        return

    print("\n=== ALL COOKIES ===")

    # Check if cookies are in storage_state format
    if 'cookies' in cookies_data:
        cookies = cookies_data['cookies']
        print(f"Found {len(cookies)} cookies in storage_state:")
    else:
        # Direct cookies array
        cookies = cookies_data if isinstance(cookies_data, list) else []
        print(f"Found {len(cookies)} cookies:")

    # Display all cookies
    for i, cookie in enumerate(cookies):
        name = cookie.get('name', 'unnamed')
        value = cookie.get('value', '')
        domain = cookie.get('domain', '')
        path = cookie.get('path', '')

        print(f"\n{i+1}. {name}")
        print(f"    Value: {value[:100]}{'...' if len(value) > 100 else ''}")
        print(f"    Domain: {domain}")
        print(f"    Path: {path}")

        # Check if this looks like a project cookie
        if 'project' in name.lower():
            print(f"    *** POTENTIAL PROJECT COOKIE ***")

def main():
    print("Loading cookies from cookies.json...")
    cookies_data = load_cookies()

    if not cookies_data:
        print("No cookies loaded")
        return

    print("\n=== EXTRACTING PROJECT COOKIES ===")
    project_cookies = extract_project_cookies(cookies_data)

    if project_cookies:
        print(f"\nFound {len(project_cookies)} project-related cookies")
    else:
        print("\nNo explicit project cookies found")

    # Display all cookies for inspection
    display_all_cookies(cookies_data)

    print("\n=== HOW TO USE ===")
    print("To scan a specific project, use one of these values with the test scanner:")
    print("- Pass the project cookie value to the scan_project_issues() function")
    print("- Or manually set the MANTIS_PROJECT_COOKIE in your cookies before scanning")
    print("\nExample usage:")
    print("  scan_project_issues('153')  # If 153 is your project ID")

if __name__ == "__main__":
    main()