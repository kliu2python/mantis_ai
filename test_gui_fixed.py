#!/usr/bin/env python3
"""
Simple test script for Mantis Dashboard GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os

def test_tkinter():
    """Test if tkinter is working"""
    try:
        root = tk.Tk()
        root.title("Tkinter Test")
        root.geometry("300x200")

        # Add a label
        label = ttk.Label(root, text="Tkinter is working!", font=("Arial", 14))
        label.pack(pady=20)

        # Add a button
        def on_click():
            messagebox.showinfo("Success", "Tkinter is properly installed!")

        button = ttk.Button(root, text="Test Message", command=on_click)
        button.pack(pady=10)

        # Add close button
        close_btn = ttk.Button(root, text="Close", command=root.destroy)
        close_btn.pack(pady=10)

        print("Tkinter test window created successfully")
        print("  Close the window to continue...")

        root.mainloop()
        return True

    except Exception as e:
        print(f"Tkinter test failed: {e}")
        return False

def test_database():
    """Test database connectivity"""
    try:
        if os.path.exists("mantis_data.db"):
            conn = sqlite3.connect("mantis_data.db")
            cursor = conn.cursor()

            # Check if we can query the database
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            print("Database test successful")
            print(f"  Found {len(tables)} tables")

            # Look for issues tables
            issues_tables = [table[0] for table in tables if table[0].startswith('issues_')]
            print(f"  Found {len(issues_tables)} issues tables")

            if issues_tables:
                # Test query on first issues table
                first_table = issues_tables[0]
                cursor.execute(f"SELECT COUNT(*) FROM {first_table}")
                count = cursor.fetchone()[0]
                print(f"  Table {first_table} contains {count} records")

            conn.close()
            return True
        else:
            print("Database file not found (this is OK if you haven't run the scanner yet)")
            return True

    except Exception as e:
        print(f"Database test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Mantis Dashboard GUI Test")
    print("=========================")

    print("\n1. Testing Tkinter GUI framework...")
    tkinter_ok = test_tkinter()

    print("\n2. Testing Database connectivity...")
    database_ok = test_database()

    print("\n" + "="*50)
    if tkinter_ok and database_ok:
        print("All tests passed!")
        print("\nYou can now run the Mantis Dashboard:")
        print("  python mantis_dashboard.py")
    else:
        print("Some tests failed. Please check the output above.")

if __name__ == "__main__":
    main()