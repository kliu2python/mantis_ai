import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import styled from 'styled-components';
import { FaSearch, FaChartBar, FaRobot, FaCog } from 'react-icons/fa';
import Header from './components/Header';
import SearchPage from './pages/SearchPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AISearchPage from './pages/AISearchPage';
import SimilarIssuesPage from './pages/SimilarIssuesPage';
import SettingsPage from './pages/SettingsPage';

const AppContainer = styled.div`
  min-height: 100vh;
  background-color: #f5f7fa;
`;

const MainContent = styled.main`
  padding: 20px;
  margin-left: 250px;
  margin-top: 80px;

  @media (max-width: 768px) {
    margin-left: 0;
    margin-top: 140px;
  }
`;

const Sidebar = styled.nav`
  position: fixed;
  left: 0;
  top: 80px;
  width: 250px;
  height: calc(100vh - 80px);
  background-color: #2c3e50;
  color: white;
  padding: 20px 0;
  overflow-y: auto;
  z-index: 100;

  @media (max-width: 768px) {
    width: 100%;
    height: 60px;
    top: 80px;
    display: flex;
    justify-content: space-around;
  }
`;

const NavItem = styled.div`
  padding: 15px 30px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: background-color 0.3s;

  &:hover {
    background-color: #34495e;
  }

  ${({ active }) => active && `
    background-color: #3498db;
  `}

  @media (max-width: 768px) {
    padding: 10px;
    flex-direction: column;
    font-size: 12px;
  }
`;

function App() {
  const [activePage, setActivePage] = useState('search');
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  // Load projects on mount
  useEffect(() => {
    // In a real app, this would fetch from an API
    const mockProjects = [
      { id: 'issues_49_FortiToken', name: 'FortiToken' },
      { id: 'issues_FortiOS', name: 'FortiOS' },
      { id: 'issues_FortiManager', name: 'FortiManager' }
    ];
    setProjects(mockProjects);
    setSelectedProject(mockProjects[0]?.id || '');
  }, []);

  const navItems = [
    { id: 'search', label: 'Search', icon: <FaSearch /> },
    { id: 'analytics', label: 'Analytics', icon: <FaChartBar /> },
    { id: 'ai-search', label: 'AI Search', icon: <FaRobot /> },
    { id: 'similar', label: 'Similar Issues', icon: <FaSearch /> },
    { id: 'settings', label: 'Settings', icon: <FaCog /> }
  ];

  return (
    <Router>
      <AppContainer>
        <Header
          projects={projects}
          selectedProject={selectedProject}
          onSelectProject={setSelectedProject}
        />

        <Sidebar>
          {navItems.map(item => (
            <NavItem
              key={item.id}
              active={activePage === item.id}
              onClick={() => setActivePage(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </NavItem>
          ))}
        </Sidebar>

        <MainContent>
          <Routes>
            <Route path="/" element={<SearchPage projectId={selectedProject} />} />
            <Route path="/search" element={<SearchPage projectId={selectedProject} />} />
            <Route path="/analytics" element={<AnalyticsPage projectId={selectedProject} />} />
            <Route path="/ai-search" element={<AISearchPage projectId={selectedProject} />} />
            <Route path="/similar/:issueId" element={<SimilarIssuesPage projectId={selectedProject} />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </MainContent>
      </AppContainer>
    </Router>
  );
}

export default App;