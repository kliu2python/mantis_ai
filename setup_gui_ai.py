#!/usr/bin/env python3
"""
Setup script for Mantis Dashboard with GUI and AI Components
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package}: {e}")
        return False

def check_package_installed(package):
    """Check if a package is already installed"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False

def main():
    print("Mantis Dashboard Setup")
    print("======================")

    # Check if we're on Windows to handle tkinter
    is_windows = sys.platform.startswith('win')

    # Required packages
    required_packages = [
        "openai",
        "numpy",
        "scikit-learn",
        "regex"
    ]

    # Optional packages for enhanced functionality
    optional_packages = [
        "matplotlib",  # For better charts
        "pandas"        # For data manipulation
    ]

    print("Checking required packages...")

    # Check and install required packages
    for package in required_packages:
        if check_package_installed(package):
            print(f"✓ {package} is already installed")
        else:
            print(f"Installing {package}...")
            if not install_package(package):
                print(f"Warning: Could not install {package}")

    # Handle tkinter separately
    try:
        import tkinter
        print("✓ tkinter is available")
    except ImportError:
        print("✗ tkinter is not available")
        if is_windows:
            print("  On Windows, tkinter should be included with Python")
            print("  If missing, please reinstall Python with tkinter support")
        else:
            print("  On Linux/Mac, you may need to install python3-tk package:")
            print("  Ubuntu/Debian: sudo apt-get install python3-tk")
            print("  macOS: brew install python-tk")

    # Install optional packages
    print("\nInstalling optional packages for enhanced functionality...")
    for package in optional_packages:
        if not check_package_installed(package):
            print(f"Installing {package}...")
            install_package(package)

    # Create a simple test script
    create_test_script()

    print("\nSetup completed!")
    print("\nTo run the dashboard:")
    print("  python mantis_dashboard.py")

    print("\nTo use AI features, set your OpenAI API key:")
    print("  Windows: set OPENAI_API_KEY=your-api-key")
    print("  Mac/Linux: export OPENAI_API_KEY=your-api-key")

def create_test_script():
    """Create a simple test script to verify installation"""
    test_script = '''
#!/usr/bin/env python3
"""
Test script to verify Mantis Dashboard installation
"""

def test_imports():
    """Test that all required modules can be imported"""
    required_modules = [
        'tkinter',
        'sqlite3',
        'openai',
        'numpy',
        'sklearn',
        'regex'
    ]

    success = True

    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module} imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import {module}: {e}")
            success = False

    return success

def test_database():
    """Test database connectivity"""
    import sqlite3
    import os

    # Check if database file exists
    if os.path.exists("mantis_data.db"):
        try:
            conn = sqlite3.connect("mantis_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()

            print(f"✓ Database connected successfully")
            print(f"  Found {len(tables)} tables")
            return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
    else:
        print("⚠ Database file not found (will be created when you run the scanner)")
        return True

if __name__ == "__main__":
    print("Testing Mantis Dashboard Installation")
    print("=====================================")

    imports_ok = test_imports()
    database_ok = test_database()

    if imports_ok and database_ok:
        print("\\n🎉 All tests passed! You're ready to use the Mantis Dashboard.")
    else:
        print("\\n⚠ Some tests failed. Please check the output above.")
'''

    with open("test_installation.py", "w") as f:
        f.write(test_script)

    print("✓ Created test_installation.py")

if __name__ == "__main__":
    main()