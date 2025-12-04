import { render, screen } from '@testing-library/react';
import App from '../App';

test('renders mantis dashboard header', () => {
  render(<App />);
  const headerElement = screen.getByText(/Mantis AI Dashboard/i);
  expect(headerElement).toBeInTheDocument();
});