import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSessionQuery, useRunSessionMutation } from '../hooks/useSession';
import { useSessionStore } from '../store/sessionStore';
import { useWorkflowSocket } from '../hooks/useWorkflowSocket';
import { WorkflowProgress } from './WorkflowProgress';
import { Skeleton, SkeletonText } from './Skeleton';
import { 
  Building2, Globe, Target, ShieldAlert,
  ArrowLeft, ListFilter, Cpu, Users, BarChart3, HelpCircle, Mail, AlertTriangle,
  RefreshCw, RotateCcw, ExternalLink
} from 'lucide-react';

export const SessionDetail: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const { data: activeSession, isLoading: loading, error, refetch: getSession } = useSessionQuery(sessionId || null);
  const { mutateAsync: runSession } = useRunSessionMutation();
  const workflowEvents = useSessionStore((state) => state.workflowEvents);
  
  // Track selected report section tab
  const [activeTab, setActiveTab] = useState<string>('company_profile');

  const handleRetryWorkflow = async () => {
    if (!sessionId) return;
    try {
      useSessionStore.getState().clearWorkflowEvents();
      await runSession(sessionId);
    } catch (err) {
      console.error('Failed to retry workflow:', err);
    }
  };

  // Trigger WS subscription when session is running
  const isRunning = activeSession?.status === 'running';
  useWorkflowSocket(isRunning ? (sessionId || null) : null);

  // Sync activeTab to first available section if needed
  useEffect(() => {
    if (activeSession?.report?.content) {
      const keys = Object.keys(activeSession.report.content);
      if (keys.length > 0 && !keys.includes(activeTab)) {
        setActiveTab(keys[0]);
      }
    }
  }, [activeSession, activeTab]);

  const isReportSession = activeSession?.status === 'done' || (activeSession?.status === 'failed' && activeSession?.report);
  const needsReport = isReportSession && !activeSession?.report;

  // Auto-fetch the report from the backend when WS sets status to done
  useEffect(() => {
    if (needsReport && !loading) {
      getSession();
    }
  }, [needsReport, loading, getSession]);

  if (!sessionId) return null;

  if (!activeSession || (loading && needsReport)) {
    return (
      <div className="flex flex-col h-full bg-slate-950 overflow-hidden">
        {/* Header Skeleton */}
        <div className="p-5 border-b border-slate-900 flex justify-between items-center bg-slate-900/20">
          <div className="space-y-2">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>

        {/* Body Workspace Skeleton */}
        <div className="flex-1 flex flex-col md:flex-row gap-6 p-6 overflow-hidden">
          {/* Sidebar Tabs Skeleton */}
          <div className="w-full md:w-56 flex-shrink-0 flex md:flex-col overflow-x-auto md:overflow-x-visible pb-2 md:pb-0 border-b md:border-b-0 border-slate-900 md:space-y-2">
            {[...Array(8)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-28 md:w-full rounded-xl flex-shrink-0" />
            ))}
          </div>

          {/* Main Document Content Skeleton */}
          <div className="flex-1 w-full bg-slate-900/10 border border-slate-900 rounded-2xl p-6 space-y-5">
            <div className="flex justify-between items-center border-b border-slate-900 pb-3">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-4 w-24 rounded-full" />
            </div>
            <SkeletonText lines={4} />
            <SkeletonText lines={3} className="mt-6" />
            <SkeletonText lines={5} className="mt-6" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !activeSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center space-y-4">
        <AlertTriangle size={48} className="text-red-500" />
        <h3 className="text-lg font-semibold text-slate-200">Failed to load session</h3>
        <p className="text-slate-400 text-sm max-w-md">{error.message || 'Session details are unavailable.'}</p>
        <div className="flex gap-3 mt-2">
          <button 
            onClick={() => navigate('/')} 
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-850 text-sm transition text-slate-300"
          >
            <ArrowLeft size={16} /> Back to dashboard
          </button>
          <button 
            onClick={() => getSession()} 
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition"
          >
            <RefreshCw size={14} /> Retry Loading
          </button>
        </div>
      </div>
    );
  }

  const sectionsConfig = [
    { id: 'company_profile', label: 'Company Profile', icon: <Building2 size={16} /> },
    { id: 'business_needs', label: 'Business Needs', icon: <Target size={16} /> },
    { id: 'signals', label: 'Research Signals', icon: <ListFilter size={16} /> },
    { id: 'financial_performance', label: 'Financial Performance', icon: <BarChart3 size={16} /> },
    { id: 'leadership', label: 'Leadership', icon: <Users size={16} /> },
    { id: 'technology_stack', label: 'Technology Stack', icon: <Cpu size={16} /> },
    { id: 'outreach_strategy', label: 'Outreach Strategy', icon: <Mail size={16} /> },
    { id: 'discovery_questions', label: 'Discovery Questions', icon: <HelpCircle size={16} /> },
  ];

  const formatFriendlyErrorMessage = (errorMsg: string | null | undefined): string => {
    if (!errorMsg) return 'An unknown error occurred.';
    
    const lower = errorMsg.toLowerCase();
    
    if (lower.includes('429') || lower.includes('quota') || lower.includes('rate_limit') || lower.includes('rate limit') || lower.includes('resource_exhausted')) {
      return "LLM Quota Exceeded: You have exceeded your LLM provider's free-tier rate limit or daily quota. Please wait a moment or configure a billing account to continue.";
    }
    
    if (lower.includes('401') || lower.includes('unauthorized') || lower.includes('api key') || lower.includes('key is not configured')) {
      return 'Authentication Error: Invalid or missing API key. Please check your config key configurations.';
    }
    
    if (lower.includes('conn') || lower.includes('refused') || lower.includes('timeout') || lower.includes('host') || lower.includes('connect')) {
      return 'Network Error: Failed to connect to downstream services. Please verify your connection and try again.';
    }
    
    let cleaned = errorMsg;
    const dictMatch = errorMsg.match(/'message':\s*'([^']+)'/) || errorMsg.match(/"message":\s*"([^"]+)"/);
    if (dictMatch && dictMatch[1]) {
      cleaned = dictMatch[1];
    } else {
      cleaned = cleaned.replace(/[{}[\]]/g, '').replace(/:\s*'/g, ': ').replace(/'/g, '').trim();
    }
    
    return cleaned;
  };

  const parseInlineMarkdown = (text: string) => {
    const parts = text.split('**');
    const nodes = parts.map((part, i) => {
      if (i % 2 === 1) {
        return <strong key={i} className="font-bold text-white">{part}</strong>;
      }
      return part.replace(/\*/g, '');
    });
    return nodes;
  };

  const renderMarkdownText = (text: any) => {
    if (!text) return 'No content available.';
    
    if (typeof text === 'object') {
      const formatObjectToMarkdown = (obj: any, indent: string = ''): string => {
        if (Array.isArray(obj)) {
          return obj.map(item => `${indent}- ${typeof item === 'object' ? formatObjectToMarkdown(item, indent + '  ').trim() : item}`).join('\n');
        } else if (obj !== null) {
          return Object.entries(obj).map(([key, value]) => {
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            if (typeof value === 'object') {
              return `${indent}**${formattedKey}:**\n${formatObjectToMarkdown(value, indent + '  ')}`;
            }
            return `${indent}**${formattedKey}:** ${value}`;
          }).join('\n');
        }
        return '';
      };
      
      text = formatObjectToMarkdown(text);
    } else if (typeof text !== 'string') {
      text = String(text);
    }
    if (typeof text === 'string') {
      text = text.replace(/\\n/g, '\n').replace(/\\-/g, '-');
      text = text.replace(/([:;.]?)\s*(?:\(\d+\)|\d+\))\s+/g, (match: string, punctuation: string) => {
        const punc = punctuation === ';' ? '.' : (punctuation || '');
        return `${punc}\n- `;
      });
    }
    
    return text.split('\n').map((line: string, idx: number) => {
      let trimmed = line.trim();
      
      trimmed = trimmed.replace(/^\*\*(.*?)\*\*/, '$1');

      if (trimmed.startsWith('###')) {
        return <h5 key={idx} className="text-sm font-bold text-slate-300 mt-4 mb-2 font-outfit">{parseInlineMarkdown(trimmed.replace(/^###\s*/, ''))}</h5>;
      }
      if (trimmed.startsWith('##')) {
        return <h4 key={idx} className="text-base font-bold text-slate-200 mt-5 mb-2.5 font-outfit">{parseInlineMarkdown(trimmed.replace(/^##\s*/, ''))}</h4>;
      }
      if (trimmed.startsWith('#')) {
        return <h3 key={idx} className="text-lg font-bold text-white mt-6 mb-3 font-outfit">{parseInlineMarkdown(trimmed.replace(/^#\s*/, ''))}</h3>;
      }
      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        return <li key={idx} className="ml-4 list-disc text-slate-300 text-sm py-1 leading-relaxed">{parseInlineMarkdown(trimmed.replace(/^[-*\s]+/, ''))}</li>;
      }
      if (/^\d+\./.test(trimmed)) {
        return <li key={idx} className="ml-4 list-decimal text-slate-300 text-sm py-1 leading-relaxed">{parseInlineMarkdown(trimmed.replace(/^\d+\.\s*/, ''))}</li>;
      }
      return trimmed ? <p key={idx} className="text-slate-350 text-sm py-1.5 leading-relaxed">{parseInlineMarkdown(trimmed)}</p> : <div key={idx} className="h-2" />;
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 overflow-hidden p-6">
      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto bg-slate-900/30 border border-slate-800 rounded-2xl p-6">
        {activeSession.status === 'pending' || activeSession.status === 'running' ? (
          <div className="min-h-full flex items-start justify-center py-6 w-full">
            <WorkflowProgress events={workflowEvents} status={activeSession.status} />
          </div>
        ) : activeSession.status === 'failed' && !activeSession.report ? (
          <div className="min-h-full flex flex-col items-center justify-start py-6 space-y-6 w-full">
            {workflowEvents.length > 0 && (
              <WorkflowProgress events={workflowEvents} status={activeSession.status} />
            )}
            <div className="max-w-md p-5 bg-red-950/20 border border-red-900/30 rounded-2xl text-center space-y-3">
              <div className="flex items-center justify-center text-red-400 gap-2">
                <AlertTriangle size={18} />
                <h4 className="text-sm font-semibold">Workflow Terminated</h4>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                The agent pipeline encountered an unrecoverable exception. No partial briefing could be compiled. Review the pipeline activity log above or retry execution.
              </p>
              {activeSession.error_message && (
                <div className="mt-2 p-3 bg-red-950/40 border border-red-900/50 rounded-xl text-xs text-red-400 text-left leading-relaxed">
                  <strong>Error Details:</strong> {formatFriendlyErrorMessage(activeSession.error_message)}
                </div>
              )}
              <button
                onClick={handleRetryWorkflow}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-semibold shadow transition"
              >
                <RotateCcw size={12} /> Retry Workflow
              </button>
            </div>
          </div>
        ) : activeSession.report ? (
          <div className="flex flex-col h-full gap-4 overflow-hidden">
            {activeSession.status === 'failed' && (
              <div className="p-4 bg-amber-950/20 border border-amber-900/30 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fadeIn flex-shrink-0">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="text-amber-500 w-5 h-5 flex-shrink-0 mt-0.5 sm:mt-0" />
                  <div className="text-left">
                    <h4 className="text-xs font-bold text-amber-400 font-outfit uppercase">Partial Briefing Loaded</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      The workflow completed with errors. Displaying best-effort findings. You can re-run the research below.
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleRetryWorkflow}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/20 rounded-xl text-xs font-semibold transition flex-shrink-0"
                >
                  <RotateCcw size={12} /> Re-run pipeline
                </button>
              </div>
            )}

            <div className="flex flex-col md:flex-row h-full gap-6 items-start overflow-hidden">
              <div className="w-full md:w-56 flex-shrink-0 flex md:flex-col overflow-x-auto md:overflow-x-visible pb-2 md:pb-0 border-b md:border-b-0 border-slate-800 md:space-y-1">
                {sectionsConfig.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setActiveTab(s.id)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-medium transition duration-150 whitespace-nowrap md:w-full ${
                      activeTab === s.id
                        ? 'bg-blue-600 text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                    }`}
                  >
                    {s.icon}
                    <span>{s.label}</span>
                  </button>
                ))}
              </div>

              <div className="flex-1 w-full bg-slate-950/40 border border-slate-850 rounded-xl p-6 overflow-y-auto max-h-[70vh]">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-5">
                  <h3 className="font-bold text-base text-slate-100 font-outfit uppercase tracking-wider">
                    {sectionsConfig.find((s) => s.id === activeTab)?.label}
                  </h3>
                  {activeSession.report.quality_score && (
                    <span className="text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700/50">
                      Quality Rating: {activeSession.report.quality_score}
                    </span>
                  )}
                </div>
                
                <div className="prose prose-invert max-w-none">
                  {activeSession.report.content && activeSession.report.content[activeTab] ? (
                    renderMarkdownText(activeSession.report.content[activeTab])
                  ) : (
                    <p className="text-slate-500 text-sm italic">Section content was not extracted or generated.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm italic">
            No report available for this session.
          </div>
        )}
      </div>
    </div>
  );
};
export default SessionDetail;
