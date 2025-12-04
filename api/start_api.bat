@echo off
REM Start Lightweight Mantis API Server

echo Starting Lightweight Mantis API Server...
echo ==========================================

REM Check if requirements are installed
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install -r requirements_light.txt
)

echo Starting server on http://localhost:5000
echo Press Ctrl+C to stop the server

python server_light.py

echo Server stopped.
pause