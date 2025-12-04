import React, { useState } from 'react';
import styled from 'styled-components';
import { FaSearch, FaExchangeAlt } from 'react-icons/fa';

const PageContainer = styled.div`
  padding: 20px;
`;

const SearchBox = styled.div`
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  text-align: center;
`;

const IssueInput = styled.input`
  width: 300px;
  padding: 15px;
  font-size: 16px;
  border: 2px solid #3498db;
  border-radius: 4px;
  outline: none;
  margin-right: 10px;

  &:focus {
    border-color: #2980b9;
  }
`;

const SearchButton = styled.button`
  background-color: #3498db;
  color: white;
  border: none;
  padding: 12px 25px;
  font-size: 16px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;

  &:hover {
    background-color: #2980b9;
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const ResultsContainer = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
`;

const IssueTable = styled.table`
  width: 100%;
  border-collapse: collapse;

  th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #eee;
  }

  th {
    background-color: #f8f9fa;
    font-weight: 600;
  }

  tr:hover {
    background-color: #f8f9fa;
  }
`;

const SimilarityBar = styled.div`
  width: 100%;
  height: 8px;
  background-color: #ecf0f1;
  border-radius: 4px;
  overflow: hidden;
`;

const SimilarityFill = styled.div`
  height: 100%;
  background-color: ${props => {
    if (props.score > 0.8) return '#27ae60';
    if (props.score > 0.6) return '#f39c12';
    return '#e74c3c';
  }};
  width: ${props => props.score * 100}%;
`;

const SimilarIssuesPage = ({ projectId }) => {
  const [issueId, setIssueId] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);

  const handleSearch = () => {
    if (!issueId.trim()) return;

    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      // Mock results
      const mockResults = [
        {
          issue_id: '002001',
          summary: 'Token synchronization fails with network timeout',
          status: 'acknowledged',
          category: 'FortiToken Mobile',
          similarity_score: 0.94
        },
        {
          issue_id: '002005',
          summary: 'Offline token validation returns incorrect results',
          status: 'assigned',
          category: 'FortiToken Core',
          similarity_score: 0.87
        },
        {
          issue_id: '002012',
          summary: 'Concurrent token requests cause database lock',
          status: 'new',
          category: 'FortiToken Backend',
          similarity_score: 0.78
        },
        {
          issue_id: '002025',
          summary: 'Token refresh mechanism fails after 24 hours',
          status: 'discuss',
          category: 'FortiToken Mobile',
          similarity_score: 0.71
        }
      ];
      setResults(mockResults);
      setLoading(false);
    }, 800);
  };

  return (
    <PageContainer>
      <h1>Find Similar Issues</h1>

      <SearchBox>
        <h2><FaExchangeAlt /> Duplicate & Related Issue Detection</h2>
        <p>Enter an issue ID to find similar or related issues</p>

        <IssueInput
          type="text"
          placeholder="Enter Issue ID (e.g., 001234)"
          value={issueId}
          onChange={(e) => setIssueId(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />

        <SearchButton
          onClick={handleSearch}
          disabled={loading || !issueId.trim()}
        >
          <FaSearch /> {loading ? 'Finding Similar Issues...' : 'Find Similar Issues'}
        </SearchButton>
      </SearchBox>

      {results.length > 0 && (
        <ResultsContainer>
          <h2>Issues Similar to #{issueId}</h2>
          <IssueTable>
            <thead>
              <tr>
                <th>ID</th>
                <th>Summary</th>
                <th>Status</th>
                <th>Category</th>
                <th>Similarity</th>
              </tr>
            </thead>
            <tbody>
              {results.map(issue => (
                <tr key={issue.issue_id}>
                  <td>{issue.issue_id}</td>
                  <td>{issue.summary}</td>
                  <td>{issue.status}</td>
                  <td>{issue.category}</td>
                  <td>
                    <div>{(issue.similarity_score * 100).toFixed(0)}%</div>
                    <SimilarityBar>
                      <SimilarityFill score={issue.similarity_score} />
                    </SimilarityBar>
                  </td>
                </tr>
              ))}
            </tbody>
          </IssueTable>
        </ResultsContainer>
      )}
    </PageContainer>
  );
};

export default SimilarIssuesPage;