import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { SessionCreate } from '../src/components/SessionCreate';
import { useSession } from '../src/hooks/useSession';

// Mock hook
vi.mock('../src/hooks/useSession', () => ({
  useSession: vi.fn(),
}));

describe('SessionCreate Component', () => {
  const mockOnSuccess = vi.fn();
  const mockCreateSession = vi.fn();
  const mockRunSession = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSession).mockReturnValue({
      createSession: mockCreateSession,
      runSession: mockRunSession,
      loading: false,
      error: null,
      listSessions: vi.fn(),
      getSession: vi.fn(),
    });
  });

  test('renders form input elements and labels', () => {
    render(<SessionCreate onSuccess={mockOnSuccess} />);
    
    expect(screen.getByLabelText(/Company Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Company Website/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Meeting Objective/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Launch Research Workflow/i })).toBeInTheDocument();
  });

  test('shows validation error for empty fields', async () => {
    render(<SessionCreate onSuccess={mockOnSuccess} />);
    
    const submitBtn = screen.getByRole('button', { name: /Launch Research Workflow/i });
    fireEvent.click(submitBtn);
    
    expect(await screen.findByText(/Company name is required/i)).toBeInTheDocument();
  });

  test('shows validation error for invalid website URL format', async () => {
    render(<SessionCreate onSuccess={mockOnSuccess} />);
    
    fireEvent.change(screen.getByPlaceholderText('e.g. Acme Corp'), { target: { value: 'Acme Corp' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. https://acmecorp.com'), { target: { value: 'acmecorp.com' } });
    fireEvent.change(screen.getByPlaceholderText(/Pitching/i), { target: { value: 'Pitching API' } });
    
    const submitBtn = screen.getByRole('button', { name: /Launch Research Workflow/i });
    fireEvent.click(submitBtn);
    
    expect(await screen.findByText(/Website URL must start with http/i)).toBeInTheDocument();
  });

  test('calls createSession and runSession on successful submit', async () => {
    mockCreateSession.mockResolvedValue({ id: 'test-session-id' });
    mockRunSession.mockResolvedValue({ status: 'queued' });

    render(<SessionCreate onSuccess={mockOnSuccess} />);
    
    fireEvent.change(screen.getByLabelText(/Company Name/i), { target: { value: 'Acme Corp' } });
    fireEvent.change(screen.getByLabelText(/Company Website/i), { target: { value: 'https://acme.org' } });
    fireEvent.change(screen.getByLabelText(/Meeting Objective/i), { target: { value: 'Sell software' } });
    
    const submitBtn = screen.getByRole('button', { name: /Launch Research Workflow/i });
    fireEvent.click(submitBtn);
    
    await waitFor(() => {
      expect(mockCreateSession).toHaveBeenCalledWith('Acme Corp', 'https://acme.org', 'Sell software');
      expect(mockRunSession).toHaveBeenCalledWith('test-session-id');
      expect(mockOnSuccess).toHaveBeenCalledWith('test-session-id');
    });
  });
});
