import { useEffect, useRef, useState, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import type { WorkflowEvent } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useWorkflowSocket(sessionId: string | null) {
  const socketRef = useRef<WebSocket | null>(null);
  const addWorkflowEvent = useSessionStore((state) => state.addWorkflowEvent);
  const updateSessionStatus = useSessionStore((state) => state.updateSessionStatus);
  const [connected, setConnected] = useState(false);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef(1000); // Start reconnect delay at 1s
  const manualCloseRef = useRef(false);

  const connect = useCallback(() => {
    if (!sessionId) return;
    
    // Reset manual close
    manualCloseRef.current = false;
    
    // Map HTTP scheme to WS scheme automatically
    const wsScheme = WS_URL.startsWith('https') ? 'wss' : 'ws';
    const wsHost = WS_URL.replace(/^https?:\/\//, '');
    const wsUrl = `${wsScheme}://${wsHost}/ws/session/${sessionId}`;
    
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelayRef.current = 1000; // Reset delay on successful connection
      console.log('WebSocket connection opened for session', sessionId);
    };

    ws.onmessage = (event) => {
      try {
        const parsedEvent: WorkflowEvent = JSON.parse(event.data);
        addWorkflowEvent(parsedEvent);

        if (parsedEvent.event === 'workflow_complete') {
          updateSessionStatus(sessionId, 'done');
          manualCloseRef.current = true; // prevent reconnect since workflow completed
          ws.close();
        } else if (parsedEvent.event === 'error') {
          updateSessionStatus(sessionId, 'failed');
          manualCloseRef.current = true; // prevent reconnect since workflow failed
          ws.close();
        }
      } catch (err) {
        console.error('Failed to parse WebSocket event payload', err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('WebSocket connection closed');
      
      // Auto-reconnect if it was not closed manually or on success/error
      if (!manualCloseRef.current) {
        const delay = reconnectDelayRef.current;
        console.log(`Reconnecting to WebSocket in ${delay}ms...`);
        reconnectTimeoutRef.current = window.setTimeout(() => {
          reconnectDelayRef.current = Math.min(delay * 2, 30000); // Max backoff 30s
          connect();
        }, delay);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket encountered an error', err);
    };
  }, [sessionId, addWorkflowEvent, updateSessionStatus]);

  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (sessionId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [sessionId, connect, disconnect]);

  return { connected, disconnect, connect };
}
export default useWorkflowSocket;
