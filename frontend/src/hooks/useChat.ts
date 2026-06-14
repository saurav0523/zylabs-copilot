import { useState, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { api } from '../api/client';
import type { ChatMessage } from '../types';

export function useChat(sessionId: string | null) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const chatMessages = useSessionStore((state) => state.chatMessages);
  const addChatMessage = useSessionStore((state) => state.addChatMessage);

  const sendMessage = useCallback(async (message: string) => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    // Add user message to state
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    };
    addChatMessage(userMsg);
    
    try {
      const data = await api.sendChatMessage(sessionId, message);
      
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: data.reply,
        created_at: new Date().toISOString()
      };
      addChatMessage(assistantMsg);
    } catch (err: any) {
      setError(err.message || 'Failed to send message');
      
      // Optionally notify user of failure
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to connect to assistant.'}`,
        created_at: new Date().toISOString()
      };
      addChatMessage(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [sessionId, addChatMessage]);

  return {
    loading,
    error,
    chatMessages,
    sendMessage
  };
}
export default useChat;
