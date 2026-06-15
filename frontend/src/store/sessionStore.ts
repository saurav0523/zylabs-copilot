import { create } from 'zustand';
import type { ChatMessage, WorkflowEvent } from '../types';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
  retryAction?: () => Promise<void> | void;
}

interface SessionState {
  workflowEvents: WorkflowEvent[];
  chatMessages: ChatMessage[];
  toasts: ToastMessage[];
  
  addWorkflowEvent: (event: WorkflowEvent) => void;
  clearWorkflowEvents: () => void;
  addChatMessage: (msg: ChatMessage) => void;
  setChatMessages: (msgs: ChatMessage[]) => void;
  addToast: (toast: Omit<ToastMessage, 'id'> & { id?: string }) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  workflowEvents: [],
  chatMessages: [],
  toasts: [],

  addWorkflowEvent: (event) => set((state) => ({ workflowEvents: [...state.workflowEvents, event] })),
  clearWorkflowEvents: () => set({ workflowEvents: [] }),
  addChatMessage: (msg) => set((state) => ({ chatMessages: [...state.chatMessages, msg] })),
  setChatMessages: (chatMessages) => set({ chatMessages }),
  addToast: (toast) => set((state) => {
    const id = toast.id || Math.random().toString(36).substring(2, 9);
    const filtered = state.toasts.filter((t) => t.id !== id);
    return { toasts: [...filtered, { ...toast, id }] };
  }),
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  clearToasts: () => set({ toasts: [] }),
}));
