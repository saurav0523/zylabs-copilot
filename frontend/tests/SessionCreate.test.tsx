import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SessionCreate } from '../src/components/SessionCreate';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the API hooks
vi.mock('../src/hooks/useSession', () => ({
  useCreateSessionMutation: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ id: 'test-session-123' }),
    isPending: false,
    error: null,
  }),
  useRunSessionMutation: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    error: null,
  }),
}));

const queryClient = new QueryClient();

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

describe('SessionCreate Component', () => {
  it('renders correctly', () => {
    renderWithProviders(<SessionCreate onSuccess={() => {}} />);
    expect(screen.getByText('Start Research Copilot')).toBeInTheDocument();
    expect(screen.getByLabelText(/Company Name/i)).toBeInTheDocument();
  });

  it('shows validation error if company name is empty', async () => {
    renderWithProviders(<SessionCreate onSuccess={() => {}} />);
    
    const submitBtn = screen.getByRole('button', { name: /Launch Research Workflow/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Company name is required.')).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid website', async () => {
    renderWithProviders(<SessionCreate onSuccess={() => {}} />);
    
    fireEvent.change(screen.getByLabelText(/Company Name/i), { target: { value: 'Test Corp' } });
    fireEvent.change(screen.getByLabelText(/Company Website/i), { target: { value: 'invalid-url' } });
    
    const submitBtn = screen.getByRole('button', { name: /Launch Research Workflow/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Website URL must start with http:// or https://')).toBeInTheDocument();
    });
  });

  it('calls onSuccess when form is valid and submitted', async () => {
    const onSuccessMock = vi.fn();
    renderWithProviders(<SessionCreate onSuccess={onSuccessMock} />);
    
    fireEvent.change(screen.getByLabelText(/Company Name/i), { target: { value: 'Test Corp' } });
    fireEvent.change(screen.getByLabelText(/Company Website/i), { target: { value: 'https://testcorp.com' } });
    fireEvent.change(screen.getByLabelText(/Meeting Objective/i), { target: { value: 'Pitching software' } });
    
    const submitBtn = screen.getByRole('button', { name: /Launch Research Workflow/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSuccessMock).toHaveBeenCalledWith('test-session-123');
    });
  });
});
