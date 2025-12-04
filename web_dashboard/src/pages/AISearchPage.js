import React, { useState } from 'react';
import styled from 'styled-components';
import { FaRobot, FaSearch } from 'react-icons/fa';

const PageContainer = styled.div`
  padding: 20px;
`;

const AISearchBox = styled.div`
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  text-align: center;
`;

const AIInput = styled.textarea`
  width: 100%;
  height: 120px;
  padding: 15px;
  font-size: 16px;
  border: 2px solid #9b59b6;
  border-radius: 4px;
  outline: none;
  resize: vertical;
  margin-bottom: 20px;

  &:focus {
    border-color: #8e44ad;
  }
`;

const SearchButton = styled.button`
  background-color: #9b59b6;
  color: white;
  border: none;
  padding: 12px 25px;
  font-size: 16px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 auto;

  &:hover {
    background-color: #8e44ad;
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const ExamplesContainer = styled.div`
  margin-top: 30px;
  text-align: left;
`;

const ExampleItem = styled.div`
  padding: 10px;
  border-left: 3px solid #9b59b6;
  margin: 10px 0;
  background-color: #f8f9fa;
  cursor: pointer;

  &:hover {
    background-color: #e8f4fc;
  }
`;

const AISearchPage = ({ projectId }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);

  const handleSearch = () => {
    if (!query.trim()) return;

    setLoading(true);
    // Simulate AI search
    setTimeout(() => {
      // Mock results
      const mockResults = [
        {
          issue_id: '001240',
          summary: 'User authentication fails with invalid token error',
          status: 'acknowledged',
          category: 'FortiToken Mobile',
          similarity_score: 0.92
        },
        {
          issue_id: '001245',
          summary: 'Token expiration handling inconsistent across platforms',
          status: 'assigned',
          category: 'FortiToken iOS',
          similarity_score: 0.87
        },
        {
          issue_id: '001250',
          summary: 'Security vulnerability in token generation algorithm',
          status: 'new',
          category: 'FortiToken Core',
          similarity_score: 0.81
        }
      ];
      setResults(mockResults);
      setLoading(false);
    }, 1000);
  };

  const exampleQueries = [
    "Find issues related to token validation errors",
    "Show me security-related bugs in the mobile app",
    "What are the common issues with push notifications?",
    "Find all bugs related to QR code scanning"
  ];

  const useExample = (example) => {
    setQuery(example);
  };

  return (
    <PageContainer>
      <h1>AI-Powered Issue Search</h1>

      <AISearchBox>
        <h2><FaRobot /> Natural Language Issue Search</h2>
        <p>Describe what you're looking for in plain English</p>

        <AIInput
          placeholder="Example: Find security issues related to token handling..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <SearchButton
          onClick={handleSearch}
          disabled={loading || !query.trim()}
        >
          <FaSearch /> {loading ? 'Analyzing...' : 'Search with AI'}
        </SearchButton>

        <ExamplesContainer>
          <h3>Try these examples:</h3>
          {exampleQueries.map((example, index) => (
            <ExampleItem
              key={index}
              onClick={() => useExample(example)}
            >
              "{example}"
            </ExampleItem>
          ))}
        </ExamplesContainer>
      </AISearchBox>

      {results.length > 0 && (
        <div>
          <h2>AI Search Results</h2>
          {results.map((issue, index) => (
            <div key={issue.issue_id} style={{
              backgroundColor: 'white',
              padding: '15px',
              marginBottom: '10px',
              borderRadius: '4px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <h3>{issue.issue_id}: {issue.summary}</h3>
              <p><strong>Status:</strong> {issue.status} | <strong>Category:</strong> {issue.category}</p>
              <p><strong>Relevance:</strong> {(issue.similarity_score * 100).toFixed(0)}%</p>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
};

export default AISearchPage;