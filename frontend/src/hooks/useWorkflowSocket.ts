import { useEffect, useRef, useState, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useQueryClient } from '@tanstack/react-query';
import type { WorkflowEvent, Session } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL  = import.meta.env.VITE_WS_URL  || API_URL;

/** Build a clean WebSocket base URL from any scheme (http/https/ws/wss). */
function resolveWsBase(raw: string): string {
  const isTls = /^(https|wss):\/\//i.test(raw);
  const scheme = isTls ? 'wss' : 'ws';
  const host = raw.replace(/^(https?|wss?):\/\//i, '');
  return `${scheme}://${host}`;
}

const WS_BASE = resolveWsBase(WS_URL);

export function useWorkflowSocket(sessionId: string | null) {
  // ── Hooks declared in a fixed, unconditional order ──────────────────────────
  const socketRef         = useRef<WebSocket | null>(null);
  const addWorkflowEvent  = useSessionStore((s) => s.addWorkflowEvent);
  const queryClient       = useQueryClient();
  const [connected, setConnected] = useState(false);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef(1000);
  const manualCloseRef    = useRef(false);

  const updateSessionStatus = useCallback((id: string, status: Session['status']) => {
    // Update individual session
    queryClient.setQueryData<Session>(['session', id], (old) => {
      if (!old) return old;
      return { ...old, status };
    });
    // Update sessions list
    queryClient.setQueryData<Session[]>(['sessions'], (old) => {
      if (!old) return old;
      return old.map(s => s.id === id ? { ...s, status } : s);
    });
  }, [queryClient]);

  const connect = useCallback(() => {
    if (!sessionId) return;

    // Guard: skip if socket is already CONNECTING or OPEN (React StrictMode fix)
    const sock = socketRef.current;
    if (sock && (sock.readyState === WebSocket.CONNECTING || sock.readyState === WebSocket.OPEN)) {
      return;
    }

    manualCloseRef.current = false;

    const wsUrl = `${WS_BASE}/ws/session/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelayRef.current = 1000;
      console.log('[WS] connected →', sessionId);
    };

    ws.onmessage = (event) => {
      try {
        const parsed: WorkflowEvent = JSON.parse(event.data);
        addWorkflowEvent(parsed);

        if (parsed.event === 'workflow_complete') {
          updateSessionStatus(sessionId, 'done');
          // Crucial: Invalidate the query so React Query fetches the newly generated Report!
          queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
          manualCloseRef.current = true;
          ws.close();
        } else if (parsed.event === 'error') {
          updateSessionStatus(sessionId, 'failed');
          queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
          manualCloseRef.current = true;
          ws.close();
        }
      } catch (err) {
        console.error('[WS] failed to parse event', err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('[WS] closed');
      if (!manualCloseRef.current) {
        const delay = reconnectDelayRef.current;
        console.log(`[WS] reconnecting in ${delay}ms…`);
        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectDelayRef.current = Math.min(delay * 2, 30_000);
          connect();
        }, delay);
      }
    };

    // onerror always fires before onclose — no need to log both
    ws.onerror = () => {};

  }, [sessionId, addWorkflowEvent, updateSessionStatus]);

  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    const ws = socketRef.current;
    if (ws && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
      ws.close();
    }
    socketRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    if (sessionId) connect();
    return () => disconnect();
  }, [sessionId, connect, disconnect]);

  return { connected, connect, disconnect };
}

export default useWorkflowSocket;
