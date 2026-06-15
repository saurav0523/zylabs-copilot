import { useMutation } from '@tanstack/react-query';
import { useSessionStore } from '../store/sessionStore';
import { api } from '../api/client';
import type { ChatMessage } from '../types';

export function useChat(sessionId: string | null) {
  const chatMessages = useSessionStore((state) => state.chatMessages);
  const addChatMessage = useSessionStore((state) => state.addChatMessage);

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      if (!sessionId) throw new Error('No session active');
      return api.sendChatMessage(sessionId, message);
    },
    onMutate: async (message) => {
      if (!sessionId) return;
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: message,
        created_at: new Date().toISOString()
      };
      addChatMessage(userMsg);
    },
    onSuccess: (data, message, context) => {
      if (!sessionId) return;
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: data.reply,
        created_at: new Date().toISOString()
      };
      addChatMessage(assistantMsg);
    },
    onError: (err: any) => {
      if (!sessionId) return;
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to connect to assistant.'}`,
        created_at: new Date().toISOString()
      };
      addChatMessage(errorMsg);
    }
  });

  return {
    loading: sendMessageMutation.isPending,
    error: sendMessageMutation.error ? sendMessageMutation.error.message : null,
    chatMessages,
    sendMessage: sendMessageMutation.mutateAsync
  };
}
export default useChat;
