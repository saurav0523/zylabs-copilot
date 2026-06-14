import React from 'react';
import type { WorkflowEvent } from '../types';
import { CheckCircle2, Circle, AlertCircle, Loader2, RefreshCw } from 'lucide-react';

interface WorkflowProgressProps {
  events: WorkflowEvent[];
  status: string;
}

interface StepState {
  name: string;
  label: string;
  description: string;
  status: 'idle' | 'running' | 'done' | 'failed';
  meta?: any;
}

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({ events, status }) => {
  
  // Define standard steps in the graph shape
  const stepsConfig = [
    { name: 'planner', label: 'Planner Node', desc: 'Analyzing objectives and selecting target pages to scrape.' },
    { name: 'researcher', label: 'Researcher Node', desc: 'Fetching full markdown content from URLs via Firecrawl.' },
    { name: 'analyst', label: 'Analyst Node', desc: 'Extracting key business signals and structured insights using LLM.' },
    { name: 'qa_check', label: 'QA Check Node', desc: 'Reviewing extraction quality score against compliance threshold.' },
    { name: 'reporter', label: 'Reporter Node', desc: 'Compiling structured findings into an 8-section executive briefing.' }
  ];

  // Derive steps status based on events
  const steps: StepState[] = stepsConfig.map((cfg) => {
    // Find latest events for this specific node
    const nodeEvents = events.filter((e) => e.node === cfg.name);
    const started = nodeEvents.find((e) => e.event === 'node_started');
    const done = nodeEvents.find((e) => e.event === 'node_done');
    const hasError = nodeEvents.find((e) => e.event === 'error') || events.find((e) => e.event === 'error' && e.node === cfg.name);

    let stepStatus: StepState['status'] = 'idle';
    let meta: any = null;

    if (done) {
      stepStatus = 'done';
      meta = done.payload;
    } else if (started) {
      stepStatus = 'running';
      meta = started.payload;
    } else if (hasError) {
      stepStatus = 'failed';
      meta = hasError.payload;
    }

    // Adjust descriptions based on actual execution payload
    let desc = cfg.desc;
    if (cfg.name === 'planner' && done && done.payload?.targets) {
      desc = `Identified ${done.payload.targets.length} targets: ${done.payload.targets.slice(0, 2).join(', ')}${done.payload.targets.length > 2 ? '...' : ''}`;
    } else if (cfg.name === 'researcher' && done && done.payload?.pages_scraped !== undefined) {
      desc = `Scraped and synthesized ${done.payload.pages_scraped} pages successfully.`;
    } else if (cfg.name === 'analyst' && done && done.payload?.signals_extracted !== undefined) {
      desc = `Structured ${done.payload.signals_extracted} key business signals from data.`;
    } else if (cfg.name === 'qa_check' && done && done.payload?.quality_score !== undefined) {
      desc = `QA Evaluation: Score ${done.payload.quality_score} (Threshold: 0.7). Feedback: ${done.payload.feedback || 'None'}`;
    } else if (cfg.name === 'qa_check' && stepStatus === 'running' && meta?.retry_count > 0) {
      desc = `Low quality detected. Re-triggering scraper (Attempt ${meta.retry_count} of 2).`;
    }

    return {
      name: cfg.name,
      label: cfg.label,
      description: desc,
      status: stepStatus,
      meta
    };
  });

  const getStepIcon = (state: StepState['status']) => {
    switch (state) {
      case 'done':
        return <CheckCircle2 className="text-emerald-400 w-6 h-6 flex-shrink-0" />;
      case 'running':
        return <Loader2 className="text-blue-400 w-6 h-6 animate-spin flex-shrink-0" />;
      case 'failed':
        return <AlertCircle className="text-red-400 w-6 h-6 flex-shrink-0" />;
      case 'idle':
      default:
        return <Circle className="text-slate-650 w-6 h-6 flex-shrink-0" />;
    }
  };

  // Filter and compile logs chronologically from events
  const progressLogs = events
    .filter((e) => e.event === 'node_progress' || e.event === 'node_started' || e.event === 'node_done' || e.event === 'error')
    .map((e) => {
      let message = '';
      if (e.event === 'node_progress') {
        message = e.payload.message || '';
      } else if (e.event === 'node_started') {
        message = `>>> Entering ${e.node.toUpperCase()} node...`;
      } else if (e.event === 'node_done') {
        message = `<<< ${e.node.toUpperCase()} node successfully completed.`;
      } else if (e.event === 'error') {
        message = `!!! Error in ${e.node.toUpperCase()}: ${e.payload.error || 'Unknown failure'}`;
      }
      return {
        timestamp: e.timestamp,
        node: e.node,
        event: e.event,
        message
      };
    });

  return (
    <div className="w-full max-w-lg mx-auto space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="font-bold text-lg text-slate-100 font-outfit">Research Pipeline Execution</h3>
          <p className="text-slate-400 text-xs mt-0.5">Monitoring multi-agent workflow nodes in real-time</p>
        </div>
        <div className="flex items-center gap-2">
          {status === 'running' && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
          )}
          <span className="text-xs text-slate-400 font-medium capitalize">{status}</span>
        </div>
      </div>

      <div className="relative pl-8">
        {/* Connector vertical line */}
        <div 
          className="absolute left-[11px] top-[14px] bottom-[14px] w-[2px] bg-slate-800 transition-all duration-500"
          style={{
            background: `linear-gradient(to bottom, 
              ${status === 'running' ? '#3b82f6' : status === 'failed' ? '#ef4444' : '#10b981'} 0%, 
              #1e293b 100%)`
          }}
        />

        <div className="space-y-8">
          {steps.map((step, idx) => {
            const isCurrent = step.status === 'running';
            const isCompleted = step.status === 'done';
            const isFailed = step.status === 'failed';
            
            return (
              <div 
                key={step.name} 
                className="relative flex gap-4 items-start animate-bubble-pop bubble-node"
                style={{ 
                  animationDelay: `${idx * 80}ms`,
                  opacity: 0,
                  animationFillMode: 'forwards'
                }}
              >
                {/* Stepper icon overlay */}
                <div className="absolute -left-[33px] bg-slate-950 rounded-full p-1 z-10 transition-transform duration-300 hover:scale-125">
                  {getStepIcon(step.status)}
                </div>

                <div className="space-y-1">
                   <h4 className={`text-sm font-semibold font-outfit transition duration-150 ${
                    isCurrent ? 'text-blue-400 font-bold' : isCompleted ? 'text-slate-500 line-through decoration-slate-700/50' : isFailed ? 'text-red-400' : 'text-slate-650'
                  }`}>
                    {step.label}
                  </h4>
                  <p className={`text-xs transition duration-150 leading-relaxed ${
                    isCurrent ? 'text-slate-300 font-medium' : isCompleted ? 'text-slate-550 line-through decoration-slate-750/35' : isFailed ? 'text-red-400/90' : 'text-slate-650'
                  }`}>
                    {step.description}
                  </p>
                  
                  {/* Specific details inside steps */}
                  {step.name === 'qa_check' && step.meta?.retry_count > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] text-amber-400/90 bg-amber-500/5 px-2 py-1 border border-amber-500/10 rounded-md mt-1.5 w-fit">
                      <RefreshCw size={10} className="animate-spin" />
                      <span>Scraper retry initiated ({step.meta.retry_count}/2)</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Activity Log Console */}
      <div className="border-t border-slate-850 pt-5 space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-[11px] font-bold text-slate-400 font-outfit tracking-wider uppercase flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${status === 'running' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
            Live Activity Log
          </h4>
          <span className="text-[9px] text-slate-500 font-mono">WS Connected</span>
        </div>
        <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-3.5 font-mono text-[10px] text-slate-400 h-44 overflow-y-auto space-y-1.5 flex flex-col-reverse">
          {progressLogs.length === 0 ? (
            <div className="text-slate-600 italic">Awaiting pipeline initialization...</div>
          ) : (
            [...progressLogs].reverse().map((log, idx) => {
              let color = 'text-slate-400';
              if (log.event === 'node_started') color = 'text-blue-400 font-semibold';
              else if (log.event === 'node_done') color = 'text-emerald-400 font-semibold';
              else if (log.event === 'error') color = 'text-red-400 font-bold';
              else if (log.event === 'node_progress' && (log.message.startsWith('Warning') || log.message.includes('Warning'))) color = 'text-amber-400';
              
              let timeStr = '00:00:00';
              try {
                const d = new Date(log.timestamp);
                if (!isNaN(d.getTime())) {
                  timeStr = d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
                } else {
                  timeStr = log.timestamp;
                }
              } catch (err) {}
              
              return (
                <div key={idx} className={`${color} leading-relaxed break-words`}>
                  <span className="text-slate-600 mr-2">[{timeStr}]</span>
                  {log.message}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
export default WorkflowProgress;
