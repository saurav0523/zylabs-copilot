import React from 'react';
import { useSessionsQuery } from '../hooks/useSession';
import { RefreshCw, History } from 'lucide-react';
import { SkeletonCard } from './Skeleton';

interface SessionListProps {
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
}

export const SessionList: React.FC<SessionListProps> = ({ activeSessionId, onSelect }) => {
  const { data: sessions = [], isLoading: loading, error, refetch } = useSessionsQuery();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
      case 'running':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse';
      case 'done':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      case 'failed':
        return 'bg-red-500/10 text-red-400 border border-red-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) {
        return dateStr;
      }
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-200 font-semibold font-outfit">
          <History size={18} className="text-blue-500" />
          <span>Research History</span>
        </div>
        <button
          onClick={() => refetch()}
          disabled={loading}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-900 rounded-lg transition duration-150 disabled:opacity-50"
          title="Refresh history"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {loading ? (
          <div className="space-y-2 p-1">
            {[...Array(4)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : error ? (
          <div className="p-6 text-center space-y-3">
            <p className="text-xs text-red-400 font-medium">Failed to load research history</p>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-xl text-[10px] font-semibold text-slate-300 transition"
            >
              <RefreshCw size={10} /> Retry
            </button>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-10 text-xs text-slate-500">
            No past research sessions.
          </div>
        ) : (
          sessions.map((s) => {
            const isActive = s.id === activeSessionId;
            return (
              <button
                key={s.id}
                onClick={() => onSelect(s.id)}
                className={`w-full text-left p-3.5 rounded-xl transition duration-150 flex flex-col gap-1.5 border ${
                  isActive
                    ? 'bg-slate-900 border-blue-600/50 shadow-md shadow-blue-500/5'
                    : 'border-transparent hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-medium text-sm text-slate-200 truncate pr-2 font-outfit">
                    {s.company_name}
                  </span>
                  <span className={`text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-md font-semibold ${getStatusColor(s.status)}`}>
                    {s.status === 'done' ? 'Completed' :
                     s.status === 'running' ? 'Running' :
                     s.status === 'failed' ? 'Failed' :
                     'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 w-full">
                  <span className="truncate max-w-[150px]">{s.website.replace(/^https?:\/\/(www\.)?/, '')}</span>
                  <span>{formatDate(s.created_at)}</span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
export default SessionList;
