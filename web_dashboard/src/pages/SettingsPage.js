import React, { useState } from 'react';
import styled from 'styled-components';
import { FaCog, FaSave, FaSync } from 'react-icons/fa';

const PageContainer = styled.div`
  padding: 20px;
`;

const SettingsCard = styled.div`
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
`;

const FormRow = styled.div`
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
`;

const Label = styled.label`
  font-weight: bold;
  margin-bottom: 5px;
  color: #333;
`;

const Input = styled.input`
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
`;

const Select = styled.select`
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
`;

const Button = styled.button`
  background-color: #3498db;
  color: white;
  border: none;
  padding: 12px 20px;
  font-size: 14px;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;

  &:hover {
    background-color: #2980b9;
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    theme: 'light',
    itemsPerPage: 50,
    autoRefresh: true,
    refreshInterval: 300,
    defaultProject: 'issues_49_FortiToken'
  });

  const [saving, setSaving] = useState(false);

  const handleChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = () => {
    setSaving(true);
    // Simulate save operation
    setTimeout(() => {
      setSaving(false);
      alert('Settings saved successfully!');
    }, 1000);
  };

  return (
    <PageContainer>
      <h1><FaCog /> Settings</h1>

      <SettingsCard>
        <h2>Display Settings</h2>

        <FormRow>
          <Label>Theme</Label>
          <Select
            value={settings.theme}
            onChange={(e) => handleChange('theme', e.target.value)}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="auto">Auto (System)</option>
          </Select>
        </FormRow>

        <FormRow>
          <Label>Items Per Page</Label>
          <Select
            value={settings.itemsPerPage}
            onChange={(e) => handleChange('itemsPerPage', parseInt(e.target.value))}
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </Select>
        </FormRow>
      </SettingsCard>

      <SettingsCard>
        <h2>Data Settings</h2>

        <FormRow>
          <Label>
            <input
              type="checkbox"
              checked={settings.autoRefresh}
              onChange={(e) => handleChange('autoRefresh', e.target.checked)}
            />
            Auto-refresh data
          </Label>
        </FormRow>

        {settings.autoRefresh && (
          <FormRow>
            <Label>Refresh Interval (seconds)</Label>
            <Input
              type="number"
              value={settings.refreshInterval}
              onChange={(e) => handleChange('refreshInterval', parseInt(e.target.value))}
              min="30"
              max="3600"
            />
          </FormRow>
        )}

        <FormRow>
          <Label>Default Project</Label>
          <Select
            value={settings.defaultProject}
            onChange={(e) => handleChange('defaultProject', e.target.value)}
          >
            <option value="issues_49_FortiToken">FortiToken</option>
            <option value="issues_FortiOS">FortiOS</option>
            <option value="issues_FortiManager">FortiManager</option>
            <option value="issues_FortiWeb">FortiWeb</option>
          </Select>
        </FormRow>
      </SettingsCard>

      <SettingsCard>
        <h2>Actions</h2>
        <Button onClick={handleSave} disabled={saving}>
          <FaSave /> {saving ? 'Saving...' : 'Save Settings'}
        </Button>
        <Button style={{ marginLeft: '10px', backgroundColor: '#95a5a6' }}>
          <FaSync /> Reset to Defaults
        </Button>
      </SettingsCard>
    </PageContainer>
  );
};

export default SettingsPage;