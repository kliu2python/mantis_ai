import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from '../App';

global.fetch = jest.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve([{ id: 'issues_sample', name: 'Sample project' }]) })
);

test('renders AI copilot heading', () => {
  const container = document.createElement('div');
  act(() => {
    createRoot(container).render(<App />);
  });
  expect(container.textContent).toMatch(/Find similar issues instantly/i);
});

test('renders AI search call-to-action', () => {
  const container = document.createElement('div');
  act(() => {
    createRoot(container).render(<App />);
  });
  expect(container.textContent).toMatch(/Search with AI/i);
});
