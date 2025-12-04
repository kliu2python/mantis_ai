#!/usr/bin/env python3
"""
Advanced AI Analyzer for Mantis Issues
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import openai
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import re

# Database file
SQLITE_DB_FILE = "mantis_data.db"

class MantisAIAnalyzer:
    def __init__(self, api_key: str = None):
        self.conn = None
        self.init_database()

        # Set up OpenAI API key if provided
        if api_key:
            openai.api_key = api_key

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

    def get_project_issues(self, project_name: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get all issues for a specific project"""
        if not self.conn:
            return []

        try:
            # Convert project name to table name
            table_name = f"issues_{project_name.replace(' ', '_')}"

            # Build query
            query = f"SELECT * FROM {table_name}"
            params = []

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = self.conn.cursor()
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

            return issues

        except Exception as e:
            print(f"Error fetching project issues: {e}")
            return []

    def preprocess_text(self, text: str) -> str:
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

    def extract_features(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Extract text features from issues for analysis"""
        features = []

        for issue in issues:
            # Combine relevant fields
            text_parts = []

            # Add summary
            if issue.get('summary'):
                text_parts.append(str(issue['summary']))

            # Add description
            if issue.get('description'):
                text_parts.append(str(issue['description']))

            # Add steps to reproduce
            if issue.get('steps_to_reproduce'):
                text_parts.append(str(issue['steps_to_reproduce']))

            # Add additional information
            if issue.get('additional_information'):
                text_parts.append(str(issue['additional_information']))

            # Combine all parts
            combined_text = ' '.join(text_parts)

            # Preprocess
            processed_text = self.preprocess_text(combined_text)

            # Only add if we have meaningful content
            if len(processed_text.split()) > 3:
                features.append(processed_text)
            else:
                # Use summary as fallback
                summary = self.preprocess_text(str(issue.get('summary', '')))
                features.append(summary if summary else "empty issue")

        return features

    def cluster_issues(self, issues: List[Dict[str, Any]], n_clusters: int = 5) -> Dict[int, List[Dict[str, Any]]]:
        """Cluster issues using TF-IDF and K-Means"""
        if len(issues) < n_clusters:
            n_clusters = max(1, len(issues))

        # Extract features
        features = self.extract_features(issues)

        if not features:
            return {0: issues}

        # Vectorize features
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(features)

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(tfidf_matrix)

        # Group issues by cluster
        clustered_issues = {}
        for i, cluster_id in enumerate(clusters):
            if cluster_id not in clustered_issues:
                clustered_issues[cluster_id] = []
            clustered_issues[cluster_id].append(issues[i])

        return clustered_issues

    def summarize_cluster(self, issues: List[Dict[str, Any]]) -> str:
        """Generate a summary for a cluster of issues"""
        if not issues:
            return "Empty cluster"

        # Extract common words from summaries
        summaries = []
        for issue in issues:
            summary = str(issue.get('summary', ''))
            if summary:
                summaries.append(self.preprocess_text(summary))

        if not summaries:
            return "Cluster with no textual content"

        # Simple word frequency analysis
        all_words = []
        for summary in summaries:
            words = summary.split()
            all_words.extend(words)

        # Get most common words (excluding common stop words conceptually)
        word_freq = {}
        for word in all_words:
            if len(word) > 2:  # Filter short words
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_words = [word for word, freq in sorted_words[:10]]

        # Get status distribution
        status_counts = {}
        for issue in issues:
            status = issue.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        # Create summary
        summary = f"Cluster of {len(issues)} issues\n"
        summary += f"Common terms: {', '.join(top_words[:5])}\n"
        summary += "Status distribution:\n"
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            summary += f"  {status}: {count}\n"

        return summary

    def find_similar_issues(self, target_issue: Dict[str, Any], all_issues: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Find issues similar to a target issue"""
        if not all_issues:
            return []

        # Extract features
        all_features = self.extract_features(all_issues)
        target_feature = self.extract_features([target_issue])

        if not target_feature or not all_features:
            return []

        # Vectorize
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        all_vectors = vectorizer.fit_transform(all_features)
        target_vector = vectorizer.transform([target_feature[0]])

        # Calculate similarities
        similarities = cosine_similarity(target_vector, all_vectors)[0]

        # Get top-k most similar (excluding the target issue itself if present)
        # Create list of (index, similarity) pairs
        indexed_similarities = list(enumerate(similarities))
        indexed_similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top-k (excluding perfect matches which might be the same issue)
        similar_issues = []
        for idx, similarity in indexed_similarities:
            if similarity < 0.999:  # Exclude nearly identical issues (possibly the same)
                similar_issues.append(all_issues[idx])
                if len(similar_issues) >= top_k:
                    break

        return similar_issues

    def generate_insights(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from issues"""
        if not issues:
            return {}

        insights = {
            'total_issues': len(issues),
            'status_distribution': {},
            'category_distribution': {},
            'priority_distribution': {},
            'top_categories': [],
            'recent_trends': {},
            'common_terms': []
        }

        # Status distribution
        for issue in issues:
            status = issue.get('status', 'Unknown')
            insights['status_distribution'][status] = insights['status_distribution'].get(status, 0) + 1

        # Category distribution
        for issue in issues:
            category = issue.get('category', 'Uncategorized')
            insights['category_distribution'][category] = insights['category_distribution'].get(category, 0) + 1

        # Priority distribution
        for issue in issues:
            priority = issue.get('priority', 'Normal')
            insights['priority_distribution'][priority] = insights['priority_distribution'].get(priority, 0) + 1

        # Top categories
        sorted_categories = sorted(insights['category_distribution'].items(),
                                  key=lambda x: x[1], reverse=True)
        insights['top_categories'] = sorted_categories[:10]

        # Common terms analysis
        features = self.extract_features(issues[:100])  # Limit to first 100 for performance
        if features:
            # Simple word frequency
            all_words = []
            for feature in features:
                words = feature.split()
                all_words.extend([w for w in words if len(w) > 3])

            word_freq = {}
            for word in all_words:
                word_freq[word] = word_freq.get(word, 0) + 1

            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            insights['common_terms'] = sorted_words[:20]

        return insights

    def query_openai(self, prompt: str, model: str = "gpt-3.5-turbo") -> str:
        """Query OpenAI API with a prompt"""
        try:
            if not openai.api_key:
                return "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."

            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant analyzing software bug tracking issues."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error querying OpenAI: {e}"

    def analyze_project_with_ai(self, project_name: str, query: str) -> str:
        """Analyze a project using AI"""
        # Get issues
        issues = self.get_project_issues(project_name, limit=100)  # Limit for performance/API costs

        if not issues:
            return "No issues found for this project."

        # Create a summary of the issues for context
        insights = self.generate_insights(issues)

        # Create prompt for OpenAI
        prompt = f"""
        I'm analyzing the '{project_name}' project which has {insights['total_issues']} issues.

        Key statistics:
        - Status distribution: {dict(list(insights['status_distribution'].items())[:5])}
        - Top categories: {dict(insights['top_categories'][:5])}
        - Common terms in issues: {[term for term, freq in insights['common_terms'][:10]]}

        User query: {query}

        Please provide insights based on this data.
        """

        # Query OpenAI
        response = self.query_openai(prompt)

        return response

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# Utility functions for standalone use
def get_env_api_key():
    """Get OpenAI API key from environment variables"""
    return os.getenv('OPENAI_API_KEY')

def main():
    """Main function for testing"""
    print("Mantis AI Analyzer")
    print("==================")

    # Initialize analyzer
    api_key = get_env_api_key()
    analyzer = MantisAIAnalyzer(api_key)

    # Example usage
    project_name = "49_FortiToken"  # Adjust based on your actual project name

    print(f"Fetching issues for project: {project_name}")
    issues = analyzer.get_project_issues(project_name, limit=50)

    if not issues:
        print("No issues found. Available projects:")
        # List available projects
        if analyzer.conn:
            try:
                cursor = analyzer.conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name LIKE 'issues_%'
                """)
                tables = cursor.fetchall()
                for table in tables:
                    print(f"  - {table[0]}")
            except Exception as e:
                print(f"Error listing projects: {e}")
        return

    print(f"Found {len(issues)} issues")

    # Generate insights
    print("\nGenerating insights...")
    insights = analyzer.generate_insights(issues)

    print(f"Total issues: {insights['total_issues']}")
    print("Status distribution:")
    for status, count in sorted(insights['status_distribution'].items(),
                               key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {status}: {count}")

    print("\nTop categories:")
    for category, count in insights['top_categories'][:5]:
        print(f"  {category}: {count}")

    # Cluster issues
    print("\nClustering issues...")
    clusters = analyzer.cluster_issues(issues[:30], n_clusters=3)  # Limit for performance

    for cluster_id, cluster_issues in clusters.items():
        print(f"\nCluster {cluster_id} ({len(cluster_issues)} issues):")
        summary = analyzer.summarize_cluster(cluster_issues)
        print(summary)

    # Find similar issues (example with first issue)
    if len(issues) > 1:
        print("\nFinding similar issues to the first issue...")
        similar = analyzer.find_similar_issues(issues[0], issues[1:10])
        print(f"Found {len(similar)} similar issues")
        for i, issue in enumerate(similar[:3]):
            print(f"  Similar issue {i+1}: {issue.get('summary', 'No summary')[:100]}...")

    # Close connection
    analyzer.close()

if __name__ == "__main__":
    main()