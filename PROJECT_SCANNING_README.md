# Project-Based Mantis Scanning

This document explains how to use the new scripts for scanning specific Mantis projects.

## Scripts Overview

### 1. `extract_project_cookies.py`
Extracts and displays project-related cookies from your `cookies.json` file.

**Usage:**
```bash
python extract_project_cookies.py
```

This will show all cookies and highlight any project-related ones.

### 2. `test_cookies.py`
Tests cookie access and verifies you can access specific projects.

**Usage:**
```bash
python test_cookies.py
```

This will open a browser window so you can visually verify:
- You're logged in correctly
- The correct project is selected
- Cookies are working

### 3. `test_project_scanner.py`
Scans a specific project in headed (non-headless) mode for visual verification.

**Usage:**
```bash
python test_project_scanner.py
```

## How to Scan a Specific Project

### Step 1: Extract Project Cookies
Run the extractor to see what project cookies you have:
```bash
python extract_project_cookies.py
```

Look for cookies named `MANTIS_PROJECT_COOKIE` or similar.

### Step 2: Test Cookie Access
Verify your cookies work and you can access the project:
```bash
python test_cookies.py
```

When prompted, enter the project ID you want to test.

### Step 3: Run Project Scanner
Use the test scanner to verify everything works:
```bash
python test_project_scanner.py
```

## Modifying for Specific Projects

To scan a specific project, you can:

1. **Modify the test_project_scanner.py script** - Change the `PROJECT_COOKIE` value at the bottom

2. **Pass project cookie directly** - Modify the `scan_project_issues()` function call

3. **Update cookies.json** - Manually edit your cookies file to set the desired project

## Running in Headed Mode

All test scripts run in headed (non-headless) mode so you can visually verify:
- Correct project is selected
- Pages load properly
- Data extraction works

## Database Output

Issues are stored in `mantis_data.db` SQLite database in the `issues` table.

You can query the database with:
```sql
sqlite3 mantis_data.db "SELECT issue_id, project_name, summary FROM issues LIMIT 10;"
```

## Next Steps

Once you've verified everything works with the test scripts:

1. You can adapt the logic for your main scanners
2. Modify the project cookie handling as needed
3. Adjust batch sizes and worker counts for performance
4. Add more sophisticated project selection logic

The key improvements in these test scripts:
- Run in headed mode for visual verification
- Handle project cookies explicitly
- Show detailed debugging information
- Process limited data for testing