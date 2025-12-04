@echo off
REM Setup script for Mantis Project Scanner

echo Setting up Mantis Project Scanner...

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Install Playwright browsers
echo Installing Playwright browsers...
playwright install chromium

echo Setup complete!
echo.
echo To run the project scanner:
echo   python mantis_scanner.py
echo.
echo To run the cookie monitor:
echo   python cookie_monitor.py --help
echo.
pause