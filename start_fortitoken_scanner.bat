@echo off
REM Script to start the FortiToken ongoing scanner

echo Starting FortiToken Ongoing Scanner...
echo ======================================

REM Start the ongoing scanner
python fortitoken_ongoing_scanner.py

echo FortiToken scanner stopped.

pause