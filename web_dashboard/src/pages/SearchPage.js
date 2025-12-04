import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { FaSearch } from 'react-icons/fa';

const PageContainer = styled.div`
  padding: 20px;
`;

const SearchBox = styled.div`
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 15px;
  font-size: 16px;
  border: 2px solid #3498db;
  border-radius: 4px;
  outline: none;

  &:focus {
    border-color: #2980b9;
  }
`;

const FilterRow = styled.div`
  display: flex;
  gap: 15px;
  margin-top: 15px;
  flex-wrap: wrap;
`;

const FilterSelect = styled.select`
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
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

const SearchPage = ({ projectId }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [issues, setIssues] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  // Mock data for demonstration
  const mockIssues = [
    {
      issue_id: '001234',
      summary: 'Token validation fails under high load',
      status: 'acknowledged',
      category: 'FortiToken Mobile',
      last_updated: '2025-12-01'
    },
    {
      issue_id: '001235',
      summary: 'Push notifications not working on iOS 14',
      status: 'assigned',
      category: 'FortiToken iOS',
      last_updated: '2025-12-02'
    },
    {
      issue_id: '001236',
      summary: 'QR code generation produces invalid codes',
      status: 'new',
      category: 'FortiToken Android',
      last_updated: '2025-12-03'
    }
  ];

  useEffect(() => {
    if (projectId) {
      // In a real app, this would fetch from API
      setIssues(mockIssues);
    }
  }, [projectId]);

  const handleSearch = () => {
    if (!searchTerm.trim()) return;

    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      const filtered = mockIssues.filter(issue =>
        issue.summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
        issue.issue_id.includes(searchTerm)
      );
      setIssues(filtered);
      setLoading(false);
    }, 500);
  };

  return (
    <PageContainer>
      <h1>Issue Search</h1>

      <SearchBox>
        <SearchInput
          type="text"
          placeholder="Search issues by keywords..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />

        <FilterRow>
          <FilterSelect
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="assigned">Assigned</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </FilterSelect>

          <button onClick={handleSearch} disabled={loading}>
            <FaSearch /> {loading ? 'Searching...' : 'Search'}
          </button>
        </FilterRow>
      </SearchBox>

      <ResultsContainer>
        <IssueTable>
          <thead>
            <tr>
              <th>ID</th>
              <th>Summary</th>
              <th>Status</th>
              <th>Category</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {issues.map(issue => (
              <tr key={issue.issue_id}>
                <td>{issue.issue_id}</td>
                <td>{issue.summary}</td>
                <td>{issue.status}</td>
                <td>{issue.category}</td>
                <td>{issue.last_updated}</td>
              </tr>
            ))}
          </tbody>
        </IssueTable>
      </ResultsContainer>
    </PageContainer>
  );
};

export default SearchPage;