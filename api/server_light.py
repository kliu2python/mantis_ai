#!/usr/bin/env python3
"""
Lightweight Backend API Server for Mantis Dashboard
Without heavy AI dependencies
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Any

# Database file
SQLITE_DB_FILE = "../mantis_data.db"

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def init_database():
    """Initialize database connection"""
    try:
        if os.path.exists(SQLITE_DB_FILE):
            conn = sqlite3.connect(SQLITE_DB_FILE)
            print("Database connected successfully")
            return conn
        else:
            print("Database file not found")
            return None
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def preprocess_text(text: str) -> str:
    """Preprocess text for analysis"""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove special characters but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def simple_text_similarity(text1: str, text2: str) -> float:
    """Simple text similarity calculation"""
    if not text1 or not text2:
        return 0.0

    # Convert to sets of words
    words1 = set(preprocess_text(text1).split())
    words2 = set(preprocess_text(text2).split())

    # Calculate Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)

    if len(union) == 0:
        return 0.0

    return len(intersection) / len(union)

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get list of available projects"""
    try:
        conn = init_database()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE 'issues_%'
        """)
        tables = cursor.fetchall()
        conn.close()

        projects = []
        for table in tables:
            table_name = table[0]
            # Extract project name from table name
            project_name = table_name.replace('issues_', '').replace('_', ' ')
            projects.append({
                'id': table_name,
                'name': project_name
            })

        return jsonify(projects)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/issues/<project_id>', methods=['GET'])
def get_issues(project_id):
    """Get issues for a specific project with optional filtering"""
    try:
        # Get query parameters
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        search = request.args.get('search', default='', type=str)
        status = request.args.get('status', default='', type=str)

        conn = init_database()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        # Build query
        query = f"SELECT * FROM {project_id}"
        conditions = []
        params = []

        # Apply filters
        if search:
            conditions.append("(summary LIKE ? OR description LIKE ? OR category LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Add ordering and pagination
        query += " ORDER BY last_updated DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, params)

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Fetch rows
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        issues = []
        for row in rows:
            issue = dict(zip(columns, row))
            issues.append(issue)

        conn.close()

        return jsonify(issues)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/issues/<project_id>/search', methods=['POST'])
def search_issues(project_id):
    """Search issues using keyword matching"""
    try:
        data = request.get_json()
        query_text = data.get('query', '')

        if not query_text:
            return jsonify({'error': 'Query text is required'}), 400

        conn = init_database()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        # Search in multiple fields
        search_query = f"""
            SELECT * FROM {project_id}
            WHERE summary LIKE ? OR description LIKE ? OR category LIKE ? OR steps_to_reproduce LIKE ?
            ORDER BY last_updated DESC
            LIMIT 100
        """

        search_param = f"%{query_text}%"
        params = [search_param, search_param, search_param, search_param]

        cursor = conn.cursor()
        cursor.execute(search_query, params)

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Fetch rows
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        issues = []
        for row in rows:
            issue = dict(zip(columns, row))
            issues.append(issue)

        conn.close()

        return jsonify(issues)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/issues/<project_id>/<issue_id>/similar', methods=['GET'])
def find_similar_issues(project_id, issue_id):
    """Find issues similar to a specific issue using simple text matching"""
    try:
        limit = request.args.get('limit', default=10, type=int)

        conn = init_database()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Get the target issue
        cursor.execute(f"SELECT * FROM {project_id} WHERE issue_id = ?", (issue_id,))
        target_issue_row = cursor.fetchone()

        if not target_issue_row:
            conn.close()
            return jsonify({'error': 'Issue not found'}), 404

        # Get column names for target issue
        columns = [description[0] for description in cursor.description]
        target_issue = dict(zip(columns, target_issue_row))

        # Create text representation of target issue
        target_text_parts = []
        for field in ['summary', 'description', 'steps_to_reproduce', 'category']:
            if target_issue.get(field):
                target_text_parts.append(str(target_issue[field]))
        target_text = ' '.join(target_text_parts)

        # Get all issues for comparison
        cursor.execute(f"SELECT * FROM {project_id} WHERE issue_id != ?", (issue_id,))
        rows = cursor.fetchall()

        conn.close()

        # Calculate similarities
        similarities = []
        for row in rows:
            issue = dict(zip(columns, row))

            # Create text representation of this issue
            issue_text_parts = []
            for field in ['summary', 'description', 'steps_to_reproduce', 'category']:
                if issue.get(field):
                    issue_text_parts.append(str(issue[field]))
            issue_text = ' '.join(issue_text_parts)

            # Calculate similarity
            similarity = simple_text_similarity(target_text, issue_text)

            # Add to results if there's some similarity
            if similarity > 0:
                issue['similarity_score'] = similarity
                similarities.append(issue)

        # Sort by similarity and limit results
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = similarities[:limit]

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/<project_id>', methods=['GET'])
def get_analytics(project_id):
    """Get analytics for a specific project"""
    try:
        conn = init_database()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Get total issues
        cursor.execute(f"SELECT COUNT(*) FROM {project_id}")
        total_issues = cursor.fetchone()[0]

        # Get status distribution
        cursor.execute(f"""
            SELECT status, COUNT(*)
            FROM {project_id}
            GROUP BY status
            ORDER BY COUNT(*) DESC
        """)
        status_dist = cursor.fetchall()

        # Get category distribution
        cursor.execute(f"""
            SELECT category, COUNT(*)
            FROM {project_id}
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        category_dist = cursor.fetchall()

        # Get recent activity
        cursor.execute(f"""
            SELECT DATE(last_updated) as date, COUNT(*)
            FROM {project_id}
            WHERE last_updated IS NOT NULL
            GROUP BY DATE(last_updated)
            ORDER BY date DESC
            LIMIT 30
        """)
        recent_activity = cursor.fetchall()

        conn.close()

        analytics = {
            'total_issues': total_issues,
            'status_distribution': dict(status_dist),
            'category_distribution': dict(category_dist),
            'recent_activity': dict(recent_activity)
        }

        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def main():
    """Main function to start the server"""
    print("Initializing Lightweight Mantis Dashboard Backend...")

    # Start the server
    print("Starting server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()