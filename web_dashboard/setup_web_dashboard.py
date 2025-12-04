#!/usr/bin/env python3
"""
Setup script for Mantis Web Dashboard
"""

import os
import subprocess
import sys

def create_directory_structure():
    """Create the necessary directory structure"""
    directories = [
        'src',
        'src/components',
        'src/pages',
        'src/services',
        'src/hooks',
        'src/styles',
        'src/assets',
        'public'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def create_basic_files():
    """Create basic files needed for the React app"""

    # Create index.js
    index_js = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
'''

    with open('src/index.js', 'w') as f:
        f.write(index_js)
    print("Created src/index.js")

    # Create App.css
    app_css = '''body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
    monospace;
}
'''

    with open('src/App.css', 'w') as f:
        f.write(app_css)
    print("Created src/App.css")

    # Create index.html in public folder
    index_html = '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta
      name="description"
      content="Mantis AI Dashboard"
    />
    <title>Mantis AI Dashboard</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
'''

    with open('public/index.html', 'w') as f:
        f.write(index_html)
    print("Created public/index.html")

def check_prerequisites():
    """Check if prerequisites are installed"""
    print("Checking prerequisites...")

    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        print(f"✓ Node.js {result.stdout.strip()} found")
    except FileNotFoundError:
        print("✗ Node.js not found. Please install Node.js from https://nodejs.org/")
        return False

    # Check npm
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        print(f"✓ npm {result.stdout.strip()} found")
    except FileNotFoundError:
        print("✗ npm not found. Please install npm (comes with Node.js)")
        return False

    return True

def install_dependencies():
    """Install npm dependencies"""
    print("Installing npm dependencies...")
    try:
        subprocess.run(['npm', 'install'], check=True)
        print("✓ npm dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install npm dependencies: {e}")
        return False
    except FileNotFoundError:
        print("✗ npm not found. Please install Node.js and npm first.")
        return False

def main():
    """Main setup function"""
    print("Mantis Web Dashboard Setup")
    print("==========================")

    # Check prerequisites
    if not check_prerequisites():
        print("\nPlease install the required prerequisites and run setup again.")
        return

    # Create directory structure
    print("\nCreating directory structure...")
    create_directory_structure()

    # Create basic files
    print("\nCreating basic files...")
    create_basic_files()

    # Install dependencies
    print("\nInstalling dependencies...")
    if install_dependencies():
        print("\nSetup completed successfully!")
        print("\nTo start the development server:")
        print("  npm start")
        print("\nTo build for production:")
        print("  npm run build")
    else:
        print("\nSetup completed with some issues.")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()