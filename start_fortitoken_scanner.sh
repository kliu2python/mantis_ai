#!/bin/bash
# Script to start the FortiToken ongoing scanner

echo "Starting FortiToken Ongoing Scanner..."
echo "======================================"

# Make sure the script is executable
chmod +x fast_project_scanner.py

# Start the ongoing scanner
python fortitoken_ongoing_scanner.py

echo "FortiToken scanner stopped."