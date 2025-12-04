#!/usr/bin/env python3
"""
Backend API Server for Mantis AI Dashboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import re
from typing import List, Dict, Any
import openai
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import faiss

# Database file
SQLITE_DB_FILE = "../mantis_data.db"

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables for AI components
embedding_model = None
issue_embeddings = {}
issue_lookup = {}

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

def init_ai_components():
    """Initialize AI components"""
    global embedding_model

    try:
        print("Initializing AI components...")
        # Initialize sentence transformer model for embeddings
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("AI components initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing AI components: {e}")
        return False

def get_project_issues(project_id: str, limit: int = None) -> List[Dict[str, Any]]:
    """Get all issues for a specific project"""
    conn = init_database()
    if not conn:
        return []

    try:
        # Build query
        query = f"SELECT * FROM {project_id}"
        params = []

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Fetch all rows
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        issues = []
        for row in rows:
            issue = dict(zip(columns, row))
            issues.append(issue)

        conn.close()
        return issues

    except Exception as e:
        print(f"Error fetching project issues: {e}")
        if conn:
            conn.close()
        return []

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

def create_issue_text_representation(issue: Dict[str, Any]) -> str:
    """Create a text representation of an issue for embedding"""
    parts = []

    if issue.get('summary'):
        parts.append(f"Summary: {issue['summary']}")

    if issue.get('description'):
        parts.append(f"Description: {issue['description']}")

    if issue.get('steps_to_reproduce'):
        parts.append(f"Steps: {issue['steps_to_reproduce']}")

    if issue.get('category'):
        parts.append(f"Category: {issue['category']}")

    if issue.get('status'):
        parts.append(f"Status: {issue['status']}")

    if issue.get('priority'):
        parts.append(f"Priority: {issue['priority']}")

    return " ".join(parts)

def build_embedding_index(project_id: str):
    """Build embedding index for a project"""
    global embedding_model, issue_embeddings, issue_lookup

    if not embedding_model:
        if not init_ai_components():
            return False

    print(f"Building embedding index for project: {project_id}")

    # Get issues
    issues = get_project_issues(project_id)

    if not issues:
        print("No issues found for project")
        return False

    # Create text representations
    texts = []
    valid_issues = []

    for i, issue in enumerate(issues):
        text = create_issue_text_representation(issue)
        if text and len(text.split()) > 3:  # Only include issues with meaningful content
            texts.append(text)
            valid_issues.append(issue)

    if not texts:
        print("No valid texts for embedding")
        return False

    # Generate embeddings
    print(f"Generating embeddings for {len(texts)} issues...")
    embeddings = embedding_model.encode(texts)

    # Store embeddings and lookup
    issue_embeddings[project_id] = embeddings
    issue_lookup[project_id] = valid_issues

    print(f"Embedding index built successfully for {len(valid_issues)} issues")
    return True

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

@app.route('/api/issues/<project_id>/ai-search', methods=['POST'])
def ai_search_issues(project_id):
    """Search issues using AI semantic search"""
    try:
        global embedding_model, issue_embeddings, issue_lookup

        data = request.get_json()
        query_text = data.get('query', '')
        limit = data.get('limit', 10)

        if not query_text:
            return jsonify({'error': 'Query text is required'}), 400

        # Initialize embeddings if not already done
        if project_id not in issue_embeddings:
            success = build_embedding_index(project_id)
            if not success:
                return jsonify({'error': 'Failed to build embedding index'}), 500

        # Get embeddings for query
        query_embedding = embedding_model.encode([query_text])

        # Get stored embeddings
        embeddings = issue_embeddings[project_id]
        issues = issue_lookup[project_id]

        # Calculate similarities
        similarities = cosine_similarity(query_embedding, embeddings)[0]

        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:limit]

        # Prepare results
        results = []
        for i, idx in enumerate(top_indices):
            similarity = similarities[idx]
            issue = issues[idx].copy()
            issue['similarity_score'] = float(similarity)
            results.append(issue)

            if len(results) >= limit:
                break

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/issues/<project_id>/<issue_id>/similar', methods=['GET'])
def find_similar_issues(project_id, issue_id):
    """Find issues similar to a specific issue"""
    try:
        global embedding_model, issue_embeddings, issue_lookup

        limit = request.args.get('limit', default=10, type=int)

        # Initialize embeddings if not already done
        if project_id not in issue_embeddings:
            success = build_embedding_index(project_id)
            if not success:
                return jsonify({'error': 'Failed to build embedding index'}), 500

        # Find the target issue
        issues = issue_lookup[project_id]
        target_issue = None
        target_idx = -1

        for i, issue in enumerate(issues):
            if str(issue.get('issue_id', '')) == str(issue_id):
                target_issue = issue
                target_idx = i
                break

        if not target_issue:
            return jsonify({'error': 'Issue not found'}), 404

        # Get embeddings
        embeddings = issue_embeddings[project_id]

        # Calculate similarities with all other issues
        target_embedding = embeddings[target_idx].reshape(1, -1)
        similarities = cosine_similarity(target_embedding, embeddings)[0]

        # Get top matches (excluding the target issue itself)
        top_indices = np.argsort(similarities)[::-1]

        # Prepare results
        results = []
        for idx in top_indices:
            if idx != target_idx:  # Skip the target issue itself
                similarity = similarities[idx]
                issue = issues[idx].copy()
                issue['similarity_score'] = float(similarity)
                results.append(issue)

                if len(results) >= limit:
                    break

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
    print("Initializing Mantis AI Dashboard Backend...")

    # Initialize AI components
    init_ai_components()

    # Start the server
    print("Starting server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()