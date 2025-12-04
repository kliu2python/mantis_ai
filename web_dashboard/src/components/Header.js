import React from 'react';
import styled from 'styled-components';
import { FaBug, FaProjectDiagram } from 'react-icons/fa';

const HeaderContainer = styled.header`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 80px;
  background-color: #34495e;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 30px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 1000;
`;

const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 24px;
  font-weight: bold;
`;

const ProjectSelector = styled.select`
  margin-left: 30px;
  padding: 8px 15px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background-color: white;
  color: #333;
  font-size: 14px;
`;

const Header = ({ projects, selectedProject, onSelectProject }) => {
  return (
    <HeaderContainer>
      <Logo>
        <FaBug />
        <span>Mantis AI Dashboard</span>
      </Logo>

      <ProjectSelector
        value={selectedProject}
        onChange={(e) => onSelectProject(e.target.value)}
      >
        {projects.map(project => (
          <option key={project.id} value={project.id}>
            <FaProjectDiagram /> {project.name}
          </option>
        ))}
      </ProjectSelector>
    </HeaderContainer>
  );
};

export default Header;