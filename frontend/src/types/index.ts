export type SessionStatus = 'pending' | 'running' | 'done' | 'failed';
export type ChatRole = 'user' | 'assistant';

export interface Report {
  id: string;
  session_id: string;
  content: {
    company_profile?: string;
    business_needs?: string;
    signals?: string;
    financial_performance?: string;
    leadership?: string;
    technology_stack?: string;
    outreach_strategy?: string;
    discovery_questions?: string;
    [key: string]: any;
  };
  sources: string[];
  quality_score: number;
  created_at: string;
}

export interface Session {
  id: string;
  company_name: string;
  website: string;
  objective: string;
  status: SessionStatus;
  error_message?: string | null;
  created_at: string;
  updated_at: string | null;
  report?: Report | null;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: ChatRole;
  content: string;
  created_at: string;
}

export type WorkflowEventType = 'node_started' | 'node_done' | 'node_progress' | 'workflow_complete' | 'error';

export interface WorkflowEvent {
  event: WorkflowEventType;
  node: string;
  timestamp: string;
  payload: {
    targets?: string[];
    pages_scraped?: number;
    signals_extracted?: number;
    quality_score?: number;
    feedback?: string;
    retry_count?: number;
    report_id?: string;
    error?: string;
    [key: string]: any;
  };
}

// REST envelopes
export interface ApiSuccessEnvelope<T> {
  data: T;
  request_id: string;
}

export interface ApiErrorEnvelope {
  error: string;
  code: string;
  request_id: string;
}
