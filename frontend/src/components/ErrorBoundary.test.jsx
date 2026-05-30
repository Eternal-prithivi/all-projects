import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ErrorBoundary from './ErrorBoundary.jsx';

function BrokenChild() {
  throw new Error('Boom');
}

describe('ErrorBoundary', () => {
  it('renders fallback UI when a child throws', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter>
        <ErrorBoundary>
          <BrokenChild />
        </ErrorBoundary>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Something Broke/i)).toBeInTheDocument();

    console.error.mockRestore();
  });
});
