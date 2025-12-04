import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const PageContainer = styled.div`
  padding: 20px;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
`;

const StatCard = styled.div`
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
`;

const StatNumber = styled.div`
  font-size: 2em;
  font-weight: bold;
  color: #3498db;
  margin: 10px 0;
`;

const ChartContainer = styled.div`
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
`;

const AnalyticsPage = ({ projectId }) => {
  const [stats, setStats] = useState({
    totalIssues: 0,
    openIssues: 0,
    closedIssues: 0,
    avgResolutionTime: 0
  });

  // Mock chart data
  const statusData = {
    labels: ['New', 'Acknowledged', 'Assigned', 'Resolved', 'Closed'],
    datasets: [
      {
        label: 'Issue Count',
        data: [12, 19, 8, 15, 10],
        backgroundColor: [
          'rgba(255, 99, 132, 0.2)',
          'rgba(54, 162, 235, 0.2)',
          'rgba(255, 206, 86, 0.2)',
          'rgba(75, 192, 192, 0.2)',
          'rgba(153, 102, 255, 0.2)',
        ],
        borderColor: [
          'rgba(255, 99, 132, 1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  const categoryData = {
    labels: ['FortiToken Mobile', 'FortiToken iOS', 'FortiToken Android', 'Web Portal', 'API'],
    datasets: [
      {
        label: 'Issues by Category',
        data: [25, 18, 22, 15, 12],
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
    ],
  };

  useEffect(() => {
    // In a real app, this would fetch from API
    setStats({
      totalIssues: 84,
      openIssues: 42,
      closedIssues: 42,
      avgResolutionTime: 3.2
    });
  }, [projectId]);

  return (
    <PageContainer>
      <h1>Project Analytics</h1>

      <StatsGrid>
        <StatCard>
          <h3>Total Issues</h3>
          <StatNumber>{stats.totalIssues}</StatNumber>
          <p>All issues in database</p>
        </StatCard>

        <StatCard>
          <h3>Open Issues</h3>
          <StatNumber>{stats.openIssues}</StatNumber>
          <p>Currently unresolved</p>
        </StatCard>

        <StatCard>
          <h3>Closed Issues</h3>
          <StatNumber>{stats.closedIssues}</StatNumber>
          <p>Resolved issues</p>
        </StatCard>

        <StatCard>
          <h3>Avg. Resolution</h3>
          <StatNumber>{stats.avgResolutionTime}d</StatNumber>
          <p>Average days to resolve</p>
        </StatCard>
      </StatsGrid>

      <ChartContainer>
        <h2>Status Distribution</h2>
        <Bar data={statusData} />
      </ChartContainer>

      <ChartContainer>
        <h2>Issues by Category</h2>
        <Bar data={categoryData} />
      </ChartContainer>
    </PageContainer>
  );
};

export default AnalyticsPage;