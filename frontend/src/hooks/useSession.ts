import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Session } from '../types';

export function useSessionsQuery() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.listSessions(),
  });
}

export function useSessionQuery(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionId ? api.getSession(sessionId) : Promise.reject('No session ID'),
    enabled: !!sessionId,
  });
}

export function useCreateSessionMutation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (variables: { companyName: string; website: string; objective: string }) => 
      api.createSession({ 
        company_name: variables.companyName, 
        website: variables.website, 
        objective: variables.objective 
      }),
    onSuccess: (newSession) => {
      // Optimistically append to the sessions list so it appears instantly
      queryClient.setQueryData<Session[]>(['sessions'], (old) => {
        return old ? [newSession, ...old] : [newSession];
      });
      // Invalidate the sessions list so it refetches in the background
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      // Pre-populate the individual session cache
      queryClient.setQueryData(['session', newSession.id], newSession);
    },
  });
}

export function useRunSessionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => api.runSession(sessionId),
    onMutate: async (sessionId) => {
      // update react query cache optimistically
      await queryClient.cancelQueries({ queryKey: ['session', sessionId] });
      await queryClient.cancelQueries({ queryKey: ['sessions'] });

      const previousSession = queryClient.getQueryData<Session>(['session', sessionId]);
      if (previousSession) {
        queryClient.setQueryData<Session>(['session', sessionId], {
          ...previousSession,
          status: 'running',
        });
      }

      const previousSessions = queryClient.getQueryData<Session[]>(['sessions']);
      if (previousSessions) {
        queryClient.setQueryData<Session[]>(['sessions'], 
          previousSessions.map(s => s.id === sessionId ? { ...s, status: 'running' } : s)
        );
      }

      return { previousSession, previousSessions };
    },
    onSuccess: (_, sessionId) => {
      // We don't invalidate here immediately because the websocket will handle updates,
      // but we could if we wanted to guarantee sync.
    },
    onError: (err, sessionId, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(['session', sessionId], context.previousSession);
      }
      if (context?.previousSessions) {
        queryClient.setQueryData(['sessions'], context.previousSessions);
      }
    },
  });
}
