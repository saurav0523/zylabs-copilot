import type { Session, ApiSuccessEnvelope } from '../types';
import { useSessionStore } from '../store/sessionStore';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err: any) {
    const errorMsg = 'Network Connection Refused: Backend server is unreachable.';
    useSessionStore.getState().addToast({
      message: errorMsg,
      type: 'error'
    });
    throw new Error(errorMsg);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  let json: any;
  try {
    json = await response.json();
  } catch (err) {
    const errorMsg = `HTTP Error ${response.status}: Failed to parse JSON response.`;
    useSessionStore.getState().addToast({
      message: errorMsg,
      type: 'error'
    });
    throw new Error(errorMsg);
  }

  if (!response.ok) {
    const errorMsg = json.error || 'API request failed';
    useSessionStore.getState().addToast({
      message: `${errorMsg} (Request ID: ${json.request_id || 'N/A'})`,
      type: 'error'
    });
    throw new Error(errorMsg);
  }
  // All successful responses follow the envelope pattern: { data: T, request_id: string }
  return (json as ApiSuccessEnvelope<T>).data;
}

export const api = {
  async listSessions(limit = 20, offset = 0): Promise<Session[]> {
    const response = await apiFetch(`${API_URL}/api/sessions?limit=${limit}&offset=${offset}`);
    return handleResponse<Session[]>(response);
  },

  async getSession(sessionId: string): Promise<Session> {
    const response = await apiFetch(`${API_URL}/api/sessions/${sessionId}`);
    return handleResponse<Session>(response);
  },

  async createSession(payload: { company_name: string; website: string; objective: string }): Promise<Session> {
    const response = await apiFetch(`${API_URL}/api/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<Session>(response);
  },

  async runSession(sessionId: string): Promise<{ status: string }> {
    const response = await apiFetch(`${API_URL}/api/sessions/${sessionId}/run`, {
      method: 'POST',
    });
    return handleResponse<{ status: string }>(response);
  },

  async sendChatMessage(sessionId: string, message: string): Promise<{ reply: string; sources: string[] }> {
    const response = await apiFetch(`${API_URL}/api/sessions/${sessionId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });
    return handleResponse<{ reply: string; sources: string[] }>(response);
  },

  async deleteSession(sessionId: string): Promise<{ status: string }> {
    const response = await apiFetch(`${API_URL}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return handleResponse<{ status: string }>(response);
  },
};
