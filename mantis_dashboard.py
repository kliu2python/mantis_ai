#!/usr/bin/env python3
"""
Mantis Project Dashboard with GUI and AI Components
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import os
from datetime import datetime
import json
import re
from collections import Counter
import threading

# Database file
SQLITE_DB_FILE = "mantis_data.db"

class MantisDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Mantis Project Dashboard")
        self.root.geometry("1200x800")

        # Initialize database connection
        self.conn = None
        self.init_database()

        # Create GUI
        self.create_widgets()

        # Load initial data
        self.load_projects()

    def init_database(self):
        """Initialize database connection"""
        try:
            if os.path.exists(SQLITE_DB_FILE):
                self.conn = sqlite3.connect(SQLITE_DB_FILE)
                print("Database connected successfully")
            else:
                print("Database file not found")
        except Exception as e:
            print(f"Error connecting to database: {e}")

    def create_widgets(self):
        """Create GUI widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.create_dashboard_tab()
        self.create_issues_tab()
        self.create_analytics_tab()
        self.create_ai_tab()

    def create_dashboard_tab(self):
        """Create dashboard tab"""
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")

        # Project selection
        project_frame = ttk.LabelFrame(self.dashboard_frame, text="Project Selection")
        project_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(project_frame, text="Select Project:").pack(side=tk.LEFT, padx=5)
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(project_frame, textvariable=self.project_var, width=30)
        self.project_combo.pack(side=tk.LEFT, padx=5)
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)

        # Refresh button
        ttk.Button(project_frame, text="Refresh", command=self.load_projects).pack(side=tk.RIGHT, padx=5)

        # Stats frame
        stats_frame = ttk.LabelFrame(self.dashboard_frame, text="Project Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        # Stats labels
        self.stats_text = tk.Text(stats_frame, height=10, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Recent issues
        recent_frame = ttk.LabelFrame(self.dashboard_frame, text="Recent Issues")
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview for recent issues
        columns = ('ID', 'Summary', 'Status', 'Last Updated')
        self.recent_tree = ttk.Treeview(recent_frame, columns=columns, show='headings')

        for col in columns:
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=150)

        # Scrollbars
        v_scroll = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        h_scroll = ttk.Scrollbar(recent_frame, orient=tk.HORIZONTAL, command=self.recent_tree.xview)
        self.recent_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Grid layout
        self.recent_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        recent_frame.grid_rowconfigure(0, weight=1)
        recent_frame.grid_columnconfigure(0, weight=1)

    def create_issues_tab(self):
        """Create issues browsing tab"""
        self.issues_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.issues_frame, text="Issues")

        # Filter frame
        filter_frame = ttk.LabelFrame(self.issues_frame, text="Filter Issues")
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # Status filter
        ttk.Label(filter_frame, text="Status:").grid(row=0, column=0, padx=5, pady=5)
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=15)
        self.status_combo.grid(row=0, column=1, padx=5, pady=5)

        # Search filter
        ttk.Label(filter_frame, text="Search:").grid(row=0, column=2, padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=3, padx=5, pady=5)
        self.search_entry.bind('<Return>', self.filter_issues)

        ttk.Button(filter_frame, text="Apply Filter", command=self.filter_issues).grid(row=0, column=4, padx=5, pady=5)

        # Issues list
        issues_list_frame = ttk.LabelFrame(self.issues_frame, text="Issues List")
        issues_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview for issues
        columns = ('ID', 'Summary', 'Status', 'Category', 'Last Updated')
        self.issues_tree = ttk.Treeview(issues_list_frame, columns=columns, show='headings')

        for col in columns:
            self.issues_tree.heading(col, text=col)
            self.issues_tree.column(col, width=120)

        # Scrollbars
        v_scroll2 = ttk.Scrollbar(issues_list_frame, orient=tk.VERTICAL, command=self.issues_tree.yview)
        h_scroll2 = ttk.Scrollbar(issues_list_frame, orient=tk.HORIZONTAL, command=self.issues_tree.xview)
        self.issues_tree.configure(yscrollcommand=v_scroll2.set, xscrollcommand=h_scroll2.set)

        # Grid layout
        self.issues_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll2.grid(row=0, column=1, sticky='ns')
        h_scroll2.grid(row=1, column=0, sticky='ew')

        issues_list_frame.grid_rowconfigure(0, weight=1)
        issues_list_frame.grid_columnconfigure(0, weight=1)

        # Bind selection event
        self.issues_tree.bind('<<TreeviewSelect>>', self.on_issue_selected)

        # Issue details
        details_frame = ttk.LabelFrame(self.issues_frame, text="Issue Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.details_text = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_analytics_tab(self):
        """Create analytics tab"""
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Analytics")

        # Charts area
        charts_frame = ttk.LabelFrame(self.analytics_frame, text="Charts & Analytics")
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Text widget for analytics display
        self.analytics_text = tk.Text(charts_frame, wrap=tk.WORD)
        self.analytics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Generate button
        ttk.Button(self.analytics_frame, text="Generate Analytics", command=self.generate_analytics).pack(pady=5)

    def create_ai_tab(self):
        """Create AI analysis tab"""
        self.ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_frame, text="AI Analysis")

        # AI input area
        ai_input_frame = ttk.LabelFrame(self.ai_frame, text="AI Query")
        ai_input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.ai_query_text = scrolledtext.ScrolledText(ai_input_frame, height=5, wrap=tk.WORD)
        self.ai_query_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Button(ai_input_frame, text="Analyze", command=self.run_ai_analysis).pack(pady=5)

        # AI output area
        ai_output_frame = ttk.LabelFrame(self.ai_frame, text="AI Response")
        ai_output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.ai_response_text = scrolledtext.ScrolledText(ai_output_frame, height=15, wrap=tk.WORD)
        self.ai_response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_projects(self):
        """Load available projects from database"""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name LIKE 'issues_%'
            """)
            tables = cursor.fetchall()

            projects = []
            for table in tables:
                table_name = table[0]
                # Extract project name from table name
                project_name = table_name.replace('issues_', '').replace('_', ' ')
                projects.append(project_name)

            self.project_combo['values'] = projects
            if projects:
                self.project_combo.set(projects[0])
                self.load_project_data(projects[0])

        except Exception as e:
            print(f"Error loading projects: {e}")

    def load_project_data(self, project_name):
        """Load data for selected project"""
        if not self.conn:
            return

        try:
            # Convert project name to table name
            table_name = f"issues_{project_name.replace(' ', '_')}"

            # Get statistics
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_issues = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT status, COUNT(*)
                FROM {table_name}
                GROUP BY status
                ORDER BY COUNT(*) DESC
            """)
            status_counts = cursor.fetchall()

            # Display statistics
            stats = f"Project: {project_name}\n"
            stats += f"Total Issues: {total_issues}\n\n"
            stats += "Status Distribution:\n"
            for status, count in status_counts:
                stats += f"  {status or 'NULL'}: {count}\n"

            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats)

            # Load recent issues
            self.load_recent_issues(table_name)

            # Load statuses for filter
            self.load_statuses(table_name)

        except Exception as e:
            print(f"Error loading project data: {e}")

    def load_recent_issues(self, table_name):
        """Load recent issues for display"""
        try:
            # Clear existing items
            for item in self.recent_tree.get_children():
                self.recent_tree.delete(item)

            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT issue_id, summary, status, last_updated
                FROM {table_name}
                ORDER BY scraped_at DESC
                LIMIT 20
            """)

            issues = cursor.fetchall()
            for issue in issues:
                self.recent_tree.insert('', tk.END, values=issue)

        except Exception as e:
            print(f"Error loading recent issues: {e}")

    def load_statuses(self, table_name):
        """Load statuses for filter dropdown"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT DISTINCT status
                FROM {table_name}
                WHERE status IS NOT NULL
                ORDER BY status
            """)

            statuses = [row[0] for row in cursor.fetchall()]
            statuses.insert(0, "All")
            self.status_combo['values'] = statuses
            self.status_combo.set("All")

        except Exception as e:
            print(f"Error loading statuses: {e}")

    def on_project_selected(self, event=None):
        """Handle project selection"""
        project_name = self.project_var.get()
        if project_name:
            self.load_project_data(project_name)

    def filter_issues(self, event=None):
        """Filter issues based on criteria"""
        if not self.conn:
            return

        project_name = self.project_var.get()
        if not project_name:
            return

        # Convert project name to table name
        table_name = f"issues_{project_name.replace(' ', '_')}"

        try:
            # Clear existing items
            for item in self.issues_tree.get_children():
                self.issues_tree.delete(item)

            # Build query
            status_filter = self.status_var.get()
            search_term = self.search_var.get()

            query = f"SELECT issue_id, summary, status, category, last_updated FROM {table_name}"
            conditions = []
            params = []

            if status_filter and status_filter != "All":
                conditions.append("status = ?")
                params.append(status_filter)

            if search_term:
                conditions.append("(summary LIKE ? OR description LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY last_updated DESC LIMIT 100"

            cursor = self.conn.cursor()
            cursor.execute(query, params)

            issues = cursor.fetchall()
            for issue in issues:
                self.issues_tree.insert('', tk.END, values=issue)

        except Exception as e:
            print(f"Error filtering issues: {e}")

    def on_issue_selected(self, event=None):
        """Handle issue selection"""
        if not self.conn:
            return

        selection = self.issues_tree.selection()
        if not selection:
            return

        item = self.issues_tree.item(selection[0])
        issue_id = item['values'][0]

        project_name = self.project_var.get()
        if not project_name:
            return

        # Convert project name to table name
        table_name = f"issues_{project_name.replace(' ', '_')}"

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT * FROM {table_name}
                WHERE issue_id = ?
            """, (issue_id,))

            issue_data = cursor.fetchone()
            if issue_data:
                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [info[1] for info in cursor.fetchall()]

                # Display issue details
                details = ""
                for i, (column, value) in enumerate(zip(columns, issue_data)):
                    if value:
                        details += f"{column}: {value}\n"
                        if i < len(columns) - 1:  # Add separator except for last item
                            details += "-" * 40 + "\n"

                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(1.0, details)

        except Exception as e:
            print(f"Error loading issue details: {e}")

    def generate_analytics(self):
        """Generate analytics for the selected project"""
        if not self.conn:
            return

        project_name = self.project_var.get()
        if not project_name:
            return

        # Convert project name to table name
        table_name = f"issues_{project_name.replace(' ', '_')}"

        try:
            analytics = f"Analytics Report for {project_name}\n"
            analytics += "=" * 50 + "\n\n"

            cursor = self.conn.cursor()

            # Total issues
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cursor.fetchone()[0]
            analytics += f"Total Issues: {total}\n\n"

            # Status distribution
            analytics += "Status Distribution:\n"
            analytics += "-" * 30 + "\n"
            cursor.execute(f"""
                SELECT status, COUNT(*)
                FROM {table_name}
                GROUP BY status
                ORDER BY COUNT(*) DESC
            """)
            for status, count in cursor.fetchall():
                percentage = (count / total) * 100 if total > 0 else 0
                analytics += f"{status or 'NULL'}: {count} ({percentage:.1f}%)\n"

            analytics += "\n"

            # Top categories
            analytics += "Top Categories:\n"
            analytics += "-" * 30 + "\n"
            cursor.execute(f"""
                SELECT category, COUNT(*)
                FROM {table_name}
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            for category, count in cursor.fetchall():
                analytics += f"{category}: {count}\n"

            analytics += "\n"

            # Issues over time (simplified)
            analytics += "Recent Activity:\n"
            analytics += "-" * 30 + "\n"
            cursor.execute(f"""
                SELECT DATE(last_updated) as date, COUNT(*)
                FROM {table_name}
                WHERE last_updated IS NOT NULL
                GROUP BY DATE(last_updated)
                ORDER BY date DESC
                LIMIT 10
            """)
            for date, count in cursor.fetchall():
                analytics += f"{date}: {count} issues updated\n"

            self.analytics_text.delete(1.0, tk.END)
            self.analytics_text.insert(1.0, analytics)

        except Exception as e:
            error_msg = f"Error generating analytics: {e}"
            self.analytics_text.delete(1.0, tk.END)
            self.analytics_text.insert(1.0, error_msg)

    def run_ai_analysis(self):
        """Run AI analysis on the issues data"""
        query = self.ai_query_text.get(1.0, tk.END).strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter an AI query")
            return

        # Show processing message
        self.ai_response_text.delete(1.0, tk.END)
        self.ai_response_text.insert(1.0, "Processing AI query...\n")

        # Run analysis in separate thread to prevent UI freezing
        thread = threading.Thread(target=self._ai_analysis_worker, args=(query,))
        thread.daemon = True
        thread.start()

    def _ai_analysis_worker(self, query):
        """Worker function for AI analysis"""
        try:
            # Simulate AI analysis (in a real implementation, this would connect to an AI service)
            response = self.simulate_ai_analysis(query)

            # Update UI in main thread
            self.root.after(0, self._update_ai_response, response)

        except Exception as e:
            error_msg = f"Error in AI analysis: {e}"
            self.root.after(0, self._update_ai_response, error_msg)

    def _update_ai_response(self, response):
        """Update AI response text in UI"""
        self.ai_response_text.delete(1.0, tk.END)
        self.ai_response_text.insert(1.0, response)

    def simulate_ai_analysis(self, query):
        """Simulate AI analysis (replace with real AI integration)"""
        project_name = self.project_var.get()
        if not project_name:
            return "No project selected"

        table_name = f"issues_{project_name.replace(' ', '_')}"

        # Simple rule-based responses
        if "common" in query.lower() and "issue" in query.lower():
            return self.get_common_issues_analysis(table_name)
        elif "trend" in query.lower():
            return self.get_trends_analysis(table_name)
        elif "priority" in query.lower():
            return self.get_priority_analysis(table_name)
        else:
            return f"AI Analysis of '{project_name}' project:\n\nQuery: {query}\n\nThis is a simulated response. In a production environment, this would connect to an AI service for real analysis of the Mantis issues data."

    def get_common_issues_analysis(self, table_name):
        """Analyze common issues"""
        try:
            cursor = self.conn.cursor()

            # Get most common words in summaries
            cursor.execute(f"SELECT summary FROM {table_name} WHERE summary IS NOT NULL")
            summaries = [row[0] for row in cursor.fetchall()]

            # Simple word frequency analysis
            words = []
            for summary in summaries:
                # Split into words and normalize
                summary_words = re.findall(r'\b[a-zA-Z]+\b', summary.lower())
                words.extend(summary_words)

            word_counter = Counter(words)
            common_words = word_counter.most_common(10)

            response = "Common Issues Analysis:\n\n"
            response += "Most frequent terms in issue summaries:\n"
            for word, count in common_words:
                if len(word) > 3:  # Filter out short words
                    response += f"  {word}: {count} occurrences\n"

            return response

        except Exception as e:
            return f"Error in common issues analysis: {e}"

    def get_trends_analysis(self, table_name):
        """Analyze trends"""
        try:
            cursor = self.conn.cursor()

            # Get issues by month
            cursor.execute(f"""
                SELECT strftime('%Y-%m', last_updated) as month, COUNT(*)
                FROM {table_name}
                WHERE last_updated IS NOT NULL
                GROUP BY strftime('%Y-%m', last_updated)
                ORDER BY month DESC
                LIMIT 6
            """)

            trends = cursor.fetchall()

            response = "Trends Analysis (Last 6 Months):\n\n"
            response += "Issues updated per month:\n"
            for month, count in trends:
                response += f"  {month}: {count} issues\n"

            return response

        except Exception as e:
            return f"Error in trends analysis: {e}"

    def get_priority_analysis(self, table_name):
        """Analyze priority-related issues"""
        try:
            cursor = self.conn.cursor()

            # Get status distribution for high-priority issues
            cursor.execute(f"""
                SELECT status, COUNT(*)
                FROM {table_name}
                WHERE priority LIKE '%high%' OR priority LIKE '%urgent%'
                GROUP BY status
                ORDER BY COUNT(*) DESC
            """)

            priority_issues = cursor.fetchall()

            response = "Priority Issues Analysis:\n\n"
            response += "Status distribution for high/urgent priority issues:\n"
            for status, count in priority_issues:
                response += f"  {status or 'NULL'}: {count} issues\n"

            return response

        except Exception as e:
            return f"Error in priority analysis: {e}"

    def __del__(self):
        """Cleanup database connection"""
        if self.conn:
            self.conn.close()

def main():
    """Main function"""
    root = tk.Tk()
    app = MantisDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()