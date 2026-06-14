import { render, screen } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import { WorkflowProgress } from '../src/components/WorkflowProgress';
import type { WorkflowEvent } from '../src/types';

describe('WorkflowProgress Component', () => {
  test('renders all five stepper nodes initially as idle', () => {
    render(<WorkflowProgress events={[]} status="pending" />);
    
    expect(screen.getByText('Planner Node')).toBeInTheDocument();
    expect(screen.getByText('Researcher Node')).toBeInTheDocument();
    expect(screen.getByText('Analyst Node')).toBeInTheDocument();
    expect(screen.getByText('QA Check Node')).toBeInTheDocument();
    expect(screen.getByText('Reporter Node')).toBeInTheDocument();
  });

  test('renders running and completed stepper states based on events', () => {
    const mockEvents: WorkflowEvent[] = [
      {
        event: 'node_started',
        node: 'planner',
        timestamp: new Date().toISOString(),
        payload: {}
      },
      {
        event: 'node_done',
        node: 'planner',
        timestamp: new Date().toISOString(),
        payload: { targets: ['https://acme.org', 'https://acme.org/about'] }
      },
      {
        event: 'node_started',
        node: 'researcher',
        timestamp: new Date().toISOString(),
        payload: {}
      }
    ];

    render(<WorkflowProgress events={mockEvents} status="running" />);
    
    // Planner should show done/derived text
    expect(screen.getByText(/Identified 2 targets: https:\/\/acme.org/i)).toBeInTheDocument();
    
    // Active running indicators should be present
    expect(screen.getByText('Researcher Node')).toHaveClass('text-blue-400');
  });

  test('displays retry triggers on qa_check failure', () => {
    const mockEvents: WorkflowEvent[] = [
      {
        event: 'node_started',
        node: 'qa_check',
        timestamp: new Date().toISOString(),
        payload: { retry_count: 1 }
      }
    ];

    render(<WorkflowProgress events={mockEvents} status="running" />);
    
    expect(screen.getByText(/Re-triggering scraper \(Attempt 1 of 2\)/i)).toBeInTheDocument();
  });
});
