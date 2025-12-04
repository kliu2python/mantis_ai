# Mantis Bug Tracker Automation System

Automatically scans all projects in Mantis Bug Tracker, extracts complete detailed issue information, and stores all data in SQLite for easy querying and analysis.

## Overview

This project provides automated tools to:
1. Manage authentication cookies for Mantis Bug Tracker
2. Scan all projects in a Mantis Bug Tracker instance
3. Extract detailed issue information from each project
4. Store both project and issue data in SQLite database
5. Find similar issues using AI-powered semantic search

The scanner successfully processes all projects and extracts comprehensive issue details including:
- Issue ID and URL
- Summary/title
- Reporter and assignee information
- Status and priority
- Category and submission date
- Bug notes/comments

## Features

- **Cookie Management**: Automated SSO login with MFA support and cookie refresh
- **Project Enumeration**: Automatically discovers all projects in Mantis
- **Detailed Data Extraction**: Collects comprehensive issue information
- **SQLite Storage**: Stores data in local SQLite database for easy access
- **AI-Powered Search**: Finds similar issues using semantic search
- **Error Handling**: Comprehensive error handling with debug capabilities

## Prerequisites

- Python 3.7+
- Playwright for Python
- Existing Mantis session cookies (cookies.json)

## Installation

1. Clone or download the repository:
   ```bash
   # If using git
   git clone <repository-url>
   cd mantis-automation
   ```

2. Install dependencies:
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. Install additional dependencies for AI features (optional):
   ```bash
   pip install sentence-transformers chromadb scikit-learn
   ```

## Configuration

The project uses environment variables for configuration:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `MANTIS_BASE_URL` | Base URL for Mantis installation | `https://mantis.fortinet.com/` |

## Usage

### Cookie Management

Manage authentication cookies for Mantis:
```bash
python main.py                    # Refresh cookies
python cookie_monitor.py          # Monitor cookie expiration
```

### Main Scanner

Run the complete scanner that extracts both projects and detailed issue information:

**Main Scanner (Pagination support + Correct project categorization):**
```bash
python mantis_scanner.py
```

**Fast Alternative (Pure parallel processing):**
```bash
python fast_mantis_scanner.py
```

This will:
1. Load existing cookies for authentication
2. Enumerate all projects in Mantis
3. Iterate through ALL pages of each project to find every issue
4. Click into each issue to extract complete detailed information
5. Correctly extract project information from the Category field on each issue page
6. Store both project and issue data in SQLite database

### AI Reranking System

Find similar Mantis issues using AI-powered semantic search:
```bash
# Build the similarity index from SQLite data
python ai_rerank_system_sqlite.py --build-index

# Search for similar issues
python ai_rerank_system_sqlite.py --search "authentication bug in FortiToken"

# Interactive search mode
python ai_rerank_system_sqlite.py --interactive
```

### Testing Database

Check the SQLite database structure and contents:
```bash
python test_sqlite_db.py
```

## Project Structure

```
├── main.py                       # Cookie management system
├── cookie_monitor.py             # Cookie expiration monitoring
├── complete_mantis_scanner_sqlite.py  # Main scanner with SQLite
├── ai_rerank_system_sqlite.py    # AI reranking system
├── enumerate_projects.py         # Project enumeration utility
├── test_sqlite_db.py             # Database testing utility
├── cookies.json                  # Session cookies (not included in repo)
├── mantis_data.db                # SQLite database for project data
├── cookie_monitor.db            # SQLite database for cookie monitoring
├── cookie_history/              # Backup directory for cookies
├── chroma_db/                    # Chroma vector database for AI search
├── CLAUDE.md                     # Project instructions
├── README_SIMPLE.md              # This file
├── requirements.txt              # Python dependencies
├── setup.sh                      # Setup script for Linux/Mac
└── setup.bat                     # Setup script for Windows
```

## How It Works

1. **Authentication**: Uses existing `cookies.json` file for Mantis authentication
2. **Project Discovery**: Navigates to Mantis and enumerates all available projects
3. **Data Extraction**: For each project, extracts detailed information including:
   - Issue metadata
   - Descriptions and summaries
   - Bugnotes/comments
   - Status, priority, and assignment information
4. **Data Storage**: Stores all collected data in SQLite database
5. **AI Enhancement**: Optionally indexes data for semantic search capabilities

## Database Schema

### Projects Table
- `id` - Auto-incrementing primary key
- `project_id` - Mantis project ID
- `project_name` - Project name
- `project_url` - Project URL
- `scanned_at` - Timestamp when scanned

### Issues Table
- `id` - Auto-incrementing primary key
- `issue_id` - Mantis issue ID
- `project_id` - Associated project ID
- Various fields for issue metadata (summary, description, status, etc.)
- `bugnotes` - JSON string containing bug note data
- `scanned_at` - Timestamp when scanned

## Troubleshooting

### No Projects Found

If the scanner reports "No projects found":
1. Verify `cookies.json` contains valid session cookies
2. Check that the MANTIS_BASE_URL is correct

### Database Issues

If you encounter database problems:
1. Run `python test_sqlite_db.py` to check database structure
2. Delete `mantis_data.db` to start fresh (data will be rescanned)

## License

This project is proprietary and intended for internal use only.