import { create } from 'zustand';
import type { Session, ChatMessage, WorkflowEvent } from '../types';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
  retryAction?: () => Promise<void> | void;
}

interface SessionState {
  sessions: Session[];
  activeSession: Session | null;
  workflowEvents: WorkflowEvent[];
  chatMessages: ChatMessage[];
  toasts: ToastMessage[];
  loading: boolean;
  error: string | null;
  
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSessionStatus: (sessionId: string, status: Session['status']) => void;
  setActiveSession: (session: Session | null) => void;
  addWorkflowEvent: (event: WorkflowEvent) => void;
  clearWorkflowEvents: () => void;
  addChatMessage: (msg: ChatMessage) => void;
  setChatMessages: (msgs: ChatMessage[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  addToast: (toast: Omit<ToastMessage, 'id'> & { id?: string }) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeSession: null,
  workflowEvents: [],
  chatMessages: [],
  toasts: [],
  loading: false,
  error: null,

  setSessions: (sessions) => set({ sessions }),
  addSession: (session) => set((state) => ({ sessions: [session, ...state.sessions] })),
  updateSessionStatus: (sessionId, status) => set((state) => {
    const updatedSessions = state.sessions.map((s) => 
      s.id === sessionId ? { ...s, status } : s
    );
    const updatedActive = state.activeSession && state.activeSession.id === sessionId 
      ? { ...state.activeSession, status } 
      : state.activeSession;
    return { sessions: updatedSessions, activeSession: updatedActive };
  }),
  setActiveSession: (session) => set({ activeSession: session, workflowEvents: [], chatMessages: [] }),
  addWorkflowEvent: (event) => set((state) => ({ workflowEvents: [...state.workflowEvents, event] })),
  clearWorkflowEvents: () => set({ workflowEvents: [] }),
  addChatMessage: (msg) => set((state) => ({ chatMessages: [...state.chatMessages, msg] })),
  setChatMessages: (chatMessages) => set({ chatMessages }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  addToast: (toast) => set((state) => {
    const id = toast.id || Math.random().toString(36).substring(2, 9);
    const filtered = state.toasts.filter((t) => t.id !== id);
    return { toasts: [...filtered, { ...toast, id }] };
  }),
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  clearToasts: () => set({ toasts: [] }),
}));
