import { useState, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { api } from '../api/client';

export function useSession() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const setSessions = useSessionStore((state) => state.setSessions);
  const addSession = useSessionStore((state) => state.addSession);
  const setActiveSession = useSessionStore((state) => state.setActiveSession);
  const updateSessionStatus = useSessionStore((state) => state.updateSessionStatus);

  const listSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to list sessions');
    } finally {
      setLoading(false);
    }
  }, [setSessions]);

  const getSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSession(sessionId);
      setActiveSession(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch session');
    } finally {
      setLoading(false);
    }
  }, [setActiveSession]);

  const createSession = useCallback(async (companyName: string, website: string, objective: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.createSession({ company_name: companyName, website, objective });
      addSession(data);
      return data;
    } catch (err: any) {
      setError(err.message || 'Failed to create session');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [addSession]);

  const runSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.runSession(sessionId);
      updateSessionStatus(sessionId, 'running');
      return data;
    } catch (err: any) {
      setError(err.message || 'Failed to run session');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [updateSessionStatus]);

  return {
    loading,
    error,
    listSessions,
    getSession,
    createSession,
    runSession
  };
}
export default useSession;
