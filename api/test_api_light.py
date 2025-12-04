#!/usr/bin/env python3
"""
Test script for Lightweight Mantis API
"""

import requests
import time

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Is the API running?")
        return False
    except Exception as e:
        print(f"✗ Health check failed with error: {e}")
        return False

def test_get_projects():
    """Test getting list of projects"""
    print("\nTesting get projects endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/projects")
        if response.status_code == 200:
            projects = response.json()
            print(f"✓ Found {len(projects)} projects")
            if projects:
                for project in projects[:3]:  # Show first 3
                    print(f"  - {project['name']} (ID: {project['id']})")
            else:
                print("  - No projects found in database")
            return True
        else:
            print(f"✗ Get projects failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Is the API running?")
        return False
    except Exception as e:
        print(f"✗ Get projects failed with error: {e}")
        return False

def test_keyword_search(project_id="issues_49_FortiToken"):
    """Test keyword search functionality"""
    print(f"\nTesting keyword search for project: {project_id}")
    try:
        # Test data
        search_data = {
            "query": "token"
        }

        response = requests.post(
            f"{BASE_URL}/api/issues/{project_id}/search",
            json=search_data
        )

        if response.status_code == 200:
            issues = response.json()
            print(f"✓ Keyword search returned {len(issues)} results")
            if issues:
                print(f"  Sample results:")
                for issue in issues[:3]:
                    summary = issue.get('summary', '')[:50] + '...' if len(issue.get('summary', '')) > 50 else issue.get('summary', '')
                    print(f"    - {issue.get('issue_id', 'N/A')}: {summary}")
            return True
        else:
            print(f"✗ Keyword search failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Is the API running?")
        return False
    except Exception as e:
        print(f"✗ Keyword search failed with error: {e}")
        return False

def main():
    """Main test function"""
    print("Lightweight Mantis API Test")
    print("===========================")

    # Test health check
    health_ok = test_health_check()

    if health_ok:
        # Test get projects
        projects_ok = test_get_projects()

        if projects_ok:
            # Test keyword search (if projects exist)
            test_keyword_search()

    print("\n" + "="*50)
    if health_ok:
        print("API tests completed successfully!")
        print("\nYou can now start the web dashboard:")
        print("  cd web_dashboard && npm start")
    else:
        print("API tests failed. Please check if the server is running:")
        print("  cd api && python server_light.py")

if __name__ == "__main__":
    main()