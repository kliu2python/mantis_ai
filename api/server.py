#!/usr/bin/env python3
"""
Backend API Server for the Mantis AI dashboard.

This version focuses on semantic similarity search that prioritizes
summary, description, and bugnotes content. It builds per-project
vector indexes from the SQLite database and exposes endpoints for
AI-powered lookup.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
import openai
from flask import Flask, jsonify, request
from flask_cors import CORS
from sentence_transformers import SentenceTransformer

# Configuration
SQLITE_DB_FILE = os.getenv("SQLITE_DB_FILE", "../mantis_data.db")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_TOP_K = int(os.getenv("SEMANTIC_TOP_K", "3"))
CANDIDATE_MULTIPLIER = int(os.getenv("SEMANTIC_CANDIDATE_MULTIPLIER", "3"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@dataclass
class IssueDocument:
    issue_id: str
    project_id: str
    summary: str
    description: str
    bugnotes: str
    status: str
    priority: str
    severity: str
    category: str
    url: str
    last_updated: str

    @property
    def source_text(self) -> str:
        """Combined text used for embeddings, with bugnotes emphasized."""
        segments = []
        if self.summary:
            segments.append(f"Summary: {self.summary}")
        if self.description:
            segments.append(f"Description: {self.description}")
        if self.bugnotes:
            # Bugnotes are prioritized by repeating them to increase weight
            segments.append(f"Bugnotes: {self.bugnotes} {self.bugnotes}")
        return " \n".join(segments)

    def as_result(self) -> Dict[str, Any]:
        """Prepare serializable payload for API responses."""
        return {
            "issue_id": self.issue_id,
            "project_id": self.project_id,
            "summary": self.summary,
            "description": self.description,
            "bugnotes": self.bugnotes,
            "status": self.status,
            "priority": self.priority,
            "severity": self.severity,
            "category": self.category,
            "url": self.url,
            "last_updated": self.last_updated,
        }


class SQLiteRepository:
    """Fetches project and issue data from the SQLite database."""

    def __init__(self, db_file: str) -> None:
        self.db_file = db_file

    def _connect(self) -> Optional[sqlite3.Connection]:
        if not os.path.exists(self.db_file):
            logger.error("Database file not found: %s", self.db_file)
            return None
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def list_projects(self) -> List[Dict[str, str]]:
        conn = self._connect()
        if not conn:
            return []

        with conn:
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name LIKE 'issues_%'
                ORDER BY name
                """
            )
            tables = cursor.fetchall()

        projects: List[Dict[str, str]] = []
        for table in tables:
            table_name = table["name"]
            project_name = table_name.replace("issues_", "").replace("_", " ")
            projects.append({"id": table_name, "name": project_name})
        return projects

    def fetch_issues(self, project_id: str) -> List[IssueDocument]:
        conn = self._connect()
        if not conn:
            return []

        with conn:
            cursor = conn.execute(f"SELECT * FROM {project_id}")
            rows = cursor.fetchall()

        issues: List[IssueDocument] = []
        for row in rows:
            row_data = dict(row)
            issues.append(
                IssueDocument(
                    issue_id=str(row_data.get("issue_id", "")),
                    project_id=project_id,
                    summary=row_data.get("summary", ""),
                    description=row_data.get("description", ""),
                    bugnotes=self._parse_bugnotes(row_data.get("bugnotes")),
                    status=row_data.get("status", ""),
                    priority=row_data.get("priority", ""),
                    severity=row_data.get("severity", ""),
                    category=row_data.get("category", ""),
                    url=row_data.get("url", ""),
                    last_updated=row_data.get("last_updated", ""),
                )
            )
        return issues

    @staticmethod
    def _parse_bugnotes(raw_bugnotes: Any) -> str:
        if raw_bugnotes in (None, "", "null"):
            return ""
        if isinstance(raw_bugnotes, str):
            try:
                parsed = json.loads(raw_bugnotes)
                if isinstance(parsed, list):
                    return " \n".join(
                        note.get("text", "")
                        if isinstance(note, dict)
                        else str(note)
                        for note in parsed[:3]
                    )
                return str(parsed)
            except json.JSONDecodeError:
                return raw_bugnotes
        return str(raw_bugnotes)


class EmbeddingBackend:
    """Handles embedding generation for multiple providers."""

    def __init__(self) -> None:
        self.provider = EMBEDDING_PROVIDER.lower()
        self.model_name = EMBEDDING_MODEL
        self.dimension = None

        if self.provider == "openai":
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_name = OPENAI_EMBEDDING_MODEL
            self.dimension = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", "1536"))
            logger.info("Using OpenAI embeddings with model %s", self.model_name)
        else:
            logger.info("Using sentence-transformers model %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str]) -> np.ndarray:
        if self.provider == "openai":
            response = openai.Embedding.create(model=self.model_name, input=texts)
            embeddings = [record["embedding"] for record in response["data"]]
            return np.array(embeddings, dtype="float32")

        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")


class ProjectVectorIndex:
    """Stores FAISS index and associated metadata."""

    def __init__(self, dimension: int) -> None:
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None

    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        if embeddings.size == 0:
            return
        normalized = embeddings.astype("float32")
        faiss.normalize_L2(normalized)
        self.embeddings = normalized
        self.index.add(normalized)
        self.metadata.extend(metadata)

    def search(self, query_embedding: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
        query = query_embedding.astype("float32")
        faiss.normalize_L2(query)
        return self.index.search(query, top_k)


class SemanticSearchService:
    """Creates per-project indexes and runs semantic search."""

    def __init__(self, repository: SQLiteRepository, embedder: EmbeddingBackend) -> None:
        self.repository = repository
        self.embedder = embedder
        self.project_indexes: Dict[str, ProjectVectorIndex] = {}

    def _ensure_index(self, project_id: str) -> Optional[ProjectVectorIndex]:
        if project_id in self.project_indexes:
            return self.project_indexes[project_id]

        issues = self.repository.fetch_issues(project_id)
        if not issues:
            logger.warning("No issues found for project %s", project_id)
            return None

        texts: List[str] = []
        metadata: List[Dict[str, Any]] = []
        for issue in issues:
            combined_text = issue.source_text
            if len(combined_text.split()) < 4:
                continue

            texts.append(combined_text)
            metadata.append(
                {
                    **issue.as_result(),
                    "combined_text": combined_text,
                }
            )

        if not texts:
            logger.warning("No valid text for embeddings in project %s", project_id)
            return None

        embeddings = self.embedder.embed(texts)
        index = ProjectVectorIndex(embeddings.shape[1])
        index.add(embeddings, metadata)
        self.project_indexes[project_id] = index
        logger.info("Built vector index for %s with %s issues", project_id, len(metadata))
        return index

    def _rerank_candidates(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        tokens = set(re.findall(r"\w+", query.lower()))
        now = datetime.utcnow()

        for candidate in candidates:
            bugnotes_text = candidate.get("bugnotes", "") or ""
            combined_text = candidate.get("combined_text", "") or ""

            overlap = 0.0
            if tokens:
                bug_tokens = bugnotes_text.lower()
                overlap = sum(1 for token in tokens if token in bug_tokens) / max(len(tokens), 1)

            recency_score = 0.0
            last_updated = candidate.get("last_updated")
            if last_updated:
                try:
                    timestamp = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
                    delta_days = (now - timestamp).days
                    recency_score = max(0.0, 1.0 - min(delta_days / 180, 1.0))
                except Exception:
                    recency_score = 0.0

            semantic_score = float(candidate.get("similarity", 0))
            contextual_overlap = 0.0
            if tokens and combined_text:
                combined_lower = combined_text.lower()
                contextual_overlap = sum(1 for token in tokens if token in combined_lower) / max(len(tokens), 1)

            candidate["score"] = (
                semantic_score * 0.7
                + overlap * 0.2
                + recency_score * 0.05
                + contextual_overlap * 0.05
            )

        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)

    def search(self, project_id: str, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        index = self._ensure_index(project_id)
        if not index:
            return []

        candidate_size = min(
            max(top_k * CANDIDATE_MULTIPLIER, top_k),
            len(index.metadata),
        )

        query_embedding = self.embedder.embed([query])
        scores, indices = index.search(query_embedding, candidate_size)

        candidates: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            payload = index.metadata[idx].copy()
            payload["similarity"] = float(score)
            candidates.append(payload)

        reranked = self._rerank_candidates(query, candidates)
        return reranked[:top_k]

    def similar_to_issue(self, project_id: str, issue_id: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        index = self._ensure_index(project_id)
        if not index or index.embeddings is None:
            return []

        target_idx = next(
            (i for i, meta in enumerate(index.metadata) if str(meta.get("issue_id")) == str(issue_id)),
            None,
        )
        if target_idx is None:
            return []

        target_vector = index.embeddings[target_idx : target_idx + 1]
        scores, indices = index.search(target_vector, min(len(index.metadata), top_k + 5))

        candidates: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == target_idx or idx < 0:
                continue
            payload = index.metadata[idx].copy()
            payload["similarity"] = float(score)
            candidates.append(payload)

        reranked = self._rerank_candidates(index.metadata[target_idx].get("combined_text", ""), candidates)
        return reranked[:top_k]


# Initialize services
repository = SQLiteRepository(SQLITE_DB_FILE)
embedder = EmbeddingBackend()
semantic_search_service = SemanticSearchService(repository, embedder)


@app.route("/api/projects", methods=["GET"])
def get_projects() -> Tuple[Any, int]:
    projects = repository.list_projects()
    if not projects:
        return jsonify({"error": "No projects found or database unavailable"}), 500
    return jsonify(projects), 200


@app.route("/api/projects/<project_id>/issues", methods=["GET"])
def get_issues(project_id: str) -> Tuple[Any, int]:
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    conn = repository._connect()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        query = f"SELECT * FROM {project_id} ORDER BY last_updated DESC LIMIT ? OFFSET ?"
        cursor = conn.execute(query, (limit, offset))
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        issues = [dict(zip(columns, row)) for row in rows]
        return jsonify(issues), 200
    except Exception as exc:
        logger.exception("Failed to fetch issues: %s", exc)
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/projects/<project_id>/semantic-search", methods=["POST"])
def semantic_search(project_id: str) -> Tuple[Any, int]:
    payload = request.get_json(force=True) or {}
    query_text = payload.get("query", "").strip()
    top_k = int(payload.get("top_k", DEFAULT_TOP_K))

    if not query_text:
        return jsonify({"error": "Query text is required"}), 400

    results = semantic_search_service.search(project_id, query_text, top_k=top_k)
    return jsonify({"results": results}), 200


@app.route("/api/projects/<project_id>/issues/<issue_id>/similar", methods=["GET"])
def similar_issues(project_id: str, issue_id: str) -> Tuple[Any, int]:
    top_k = request.args.get("top_k", default=DEFAULT_TOP_K, type=int)
    results = semantic_search_service.similar_to_issue(project_id, issue_id, top_k=top_k)
    if not results:
        return jsonify({"error": "No similar issues found"}), 404
    return jsonify({"results": results}), 200


@app.route("/api/health", methods=["GET"])
def health_check() -> Tuple[Any, int]:
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200


def main() -> None:
    logger.info("Starting Mantis AI backend with DB file %s", SQLITE_DB_FILE)
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
