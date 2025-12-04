# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python script that automates cookie management for Mantis Bug Tracker. It uses Playwright to handle SSO authentication and automatically refresh cookies to maintain session state.

## Key Components

1. **main.py** - Core script containing:
   - SSO login handler with MFA support
   - Cookie backup and refresh functionality
   - Playwright automation for browser interactions

2. **cookies.json** - Storage for session cookies

3. **cookie_history/** - Directory for cookie backups with timestamps

## Architecture

The script follows a linear execution flow:
1. Loads existing cookies if available
2. Opens Mantis URL with current cookies
3. Detects if login is required (expired cookies)
4. Performs SSO login with MFA support if needed
5. Saves refreshed cookies to file
6. Maintains backup copies in cookie_history/

## Development Commands

### Running the Script
```bash
python main.py
```

### Dependencies
- playwright-python
- Standard Python libraries (json, os, datetime)

### Installing Dependencies
```bash
pip install playwright
playwright install chromium
```

## Code Structure

The code is organized into functional sections:
- Configuration constants at the top
- SSO login handler function
- Cookie backup utility
- Main cookie refresh logic
- Entry point guard

Key selectors and URLs are configurable as constants to facilitate maintenance.