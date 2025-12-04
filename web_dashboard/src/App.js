import React, { useEffect, useMemo, useState } from 'react';
import { FaBug, FaMagic, FaSearch } from 'react-icons/fa';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

const promptTemplates = [
  'Authentication fails when token is refreshed',
  'Crash when switching tenants on the dashboard',
  'Regression in push notification delivery timing',
  'Incorrect permissions after role changes',
];

function StatBadge({ label, value }) {
  return (
    <div className="stat-badge">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function IssueResult({ issue }) {
  return (
    <article className="issue-card">
      <header className="issue-card__header">
        <div>
          <p className="issue-id">#{issue.issue_id}</p>
          <h3 className="issue-title">{issue.summary || 'Untitled issue'}</h3>
        </div>
        <span className="issue-score">{Math.round((issue.score || issue.similarity || 0) * 100)}%</span>
      </header>

      <p className="issue-description">{issue.description || 'No description provided.'}</p>

      {issue.bugnotes && (
        <div className="issue-bugnotes">
          <p className="label">Bugnotes focus</p>
          <p>{issue.bugnotes}</p>
        </div>
      )}

      <footer className="issue-footer">
        <div className="chip-row">
          {issue.status && <span className="chip">Status: {issue.status}</span>}
          {issue.priority && <span className="chip">Priority: {issue.priority}</span>}
          {issue.severity && <span className="chip">Severity: {issue.severity}</span>}
          {issue.category && <span className="chip">Category: {issue.category}</span>}
        </div>
        {issue.url && (
          <a href={issue.url} target="_blank" rel="noreferrer" className="link">
            Open in Mantis
          </a>
        )}
      </footer>
    </article>
  );
}

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [query, setQuery] = useState('');
  const [issueAnchor, setIssueAnchor] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    const loadProjects = async () => {
      if (typeof fetch !== 'function') {
        setProjects([{ id: 'issues_sample', name: 'Sample project' }]);
        setSelectedProject('issues_sample');
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/api/projects`);
        if (!response.ok) {
          throw new Error('Unable to load projects');
        }
        const data = await response.json();
        if (active) {
          setProjects(data);
          setSelectedProject(data[0]?.id || '');
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setProjects([{ id: 'issues_sample', name: 'Sample project' }]);
          setSelectedProject('issues_sample');
          setError('Falling back to sample project list.');
        }
      }
    };

    loadProjects();
    return () => {
      active = false;
    };
  }, []);

  const activeProjectName = useMemo(
    () => projects.find((p) => p.id === selectedProject)?.name || 'Project',
    [projects, selectedProject]
  );

  const runSemanticSearch = async () => {
    if (!query.trim() || !selectedProject) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/api/projects/${selectedProject}/semantic-search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 3 }),
      });
      if (!response.ok) {
        throw new Error('Search request failed');
      }
      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      console.error(err);
      setError('Unable to run AI search. Please verify the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const runAnchorSearch = async () => {
    if (!issueAnchor.trim() || !selectedProject) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(
        `${API_BASE}/api/projects/${selectedProject}/issues/${issueAnchor}/similar?top_k=3`
      );
      if (!response.ok) {
        throw new Error('Similar issue lookup failed');
      }
      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      console.error(err);
      setError('Unable to fetch neighbors for that issue.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero__brand">
          <div className="logo">
            <FaBug />
          </div>
          <div>
            <p className="eyebrow">Mantis AI Copilot</p>
            <h1>Find similar issues instantly</h1>
            <p className="subtitle">
              Semantic matching that emphasizes summary, description, and bugnotes to surface the closest
              matches in your existing database.
            </p>
          </div>
        </div>

        <div className="hero__actions">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="selector"
          >
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <StatBadge label="Top-K" value="3" />
          <StatBadge label="Focus" value="Summary/Description/Bugnotes" />
        </div>
      </header>

      <main className="layout">
        <section className="panel">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Semantic search</p>
              <h2>Search {activeProjectName}</h2>
            </div>
            <div className="prompt-row">
              <FaMagic />
              <span>Use AI templates</span>
            </div>
          </div>

          <textarea
            className="input"
            placeholder="Describe the issue you want to match, including symptoms and context..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          <div className="prompt-chip-row">
            {promptTemplates.map((prompt) => (
              <button key={prompt} className="chip chip--ghost" onClick={() => setQuery(prompt)}>
                {prompt}
              </button>
            ))}
          </div>

          <div className="actions-row">
            <button className="btn" onClick={runSemanticSearch} disabled={loading}>
              <FaMagic /> {loading ? 'Thinking...' : 'Search with AI'}
            </button>

            <div className="anchor-search">
              <input
                className="input anchor-input"
                placeholder="Existing issue ID (e.g., 002341)"
                value={issueAnchor}
                onChange={(e) => setIssueAnchor(e.target.value)}
              />
              <button className="btn btn--ghost" onClick={runAnchorSearch} disabled={loading}>
                <FaSearch /> Find similar to issue
              </button>
            </div>
          </div>

          {error && <div className="banner banner--warning">{error}</div>}
        </section>

        <section className="panel results-panel">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Results</p>
              <h2>Top semantic matches</h2>
            </div>
            <span className="badge">k=3</span>
          </div>

          {loading && <div className="loader">Analyzing project knowledge…</div>}

          {!loading && results.length === 0 && (
            <div className="empty-state">
              <FaMagic size={24} />
              <p>Run a search to see the closest issues ranked by bugnotes and recency.</p>
            </div>
          )}

          {!loading &&
            results.map((issue) => <IssueResult key={`${issue.project_id}-${issue.issue_id}`} issue={issue} />)}
        </section>
      </main>
    </div>
  );
}

export default App;
