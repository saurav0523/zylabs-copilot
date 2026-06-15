import React, { useState } from 'react';
import { Routes, Route, useNavigate, useMatch } from 'react-router-dom';
import { useSessionQuery } from './hooks/useSession';
import { SessionList } from './components/SessionList';
import { SessionDetail } from './components/SessionDetail';
import { SessionCreate } from './components/SessionCreate';
import { ChatPanel } from './components/ChatPanel';
import { Compass, Plus, MessageSquare, Menu, X, Globe, ExternalLink } from 'lucide-react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastContainer } from './components/ToastContainer';

export const App: React.FC = () => {
  const match = useMatch('/session/:sessionId');
  const sessionId = match?.params.sessionId || null;
  const { data: activeSession } = useSessionQuery(sessionId);

  const navigate = useNavigate();

  // Mobile sidebar controls
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  // Chat resizer state
  const [chatWidth, setChatWidth] = useState(384);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = (e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  };

  React.useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX;
      const maxWidth = Math.max(300, Math.min(500, window.innerWidth - 950));
      
      if (newWidth >= 280 && newWidth <= maxWidth) {
        setChatWidth(newWidth);
      } else if (newWidth > maxWidth) {
        setChatWidth(maxWidth);
      } else if (newWidth < 280) {
        setChatWidth(280);
      }
    };
    const handleMouseUp = () => setIsResizing(false);
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleSelectSession = (id: string) => {
    navigate(`/session/${id}`);
    setSidebarOpen(false);
    setChatOpen(false);
  };

  const handleLaunchNew = () => {
    navigate('/');
    setSidebarOpen(false);
    setChatOpen(false);
  };

  const showCreator = !sessionId;

  return (
    <ErrorBoundary>
      <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      
      {/* 1. Mobile Sidebar Hamburger */}
      <div className="lg:hidden absolute top-4 left-4 z-40">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 hover:text-white"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* 2. Mobile Chat Sidebar Trigger */}
      {activeSession?.status === 'done' && (
        <div className="lg:hidden absolute top-4 right-4 z-40">
          <button
            onClick={() => setChatOpen(!chatOpen)}
            className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 hover:text-white"
          >
            {chatOpen ? <X size={20} /> : <MessageSquare size={20} />}
          </button>
        </div>
      )}

      {/* 3. Session list panel (Left) */}
      <div className={`fixed inset-y-0 left-0 transform lg:relative lg:translate-x-0 transition-transform duration-200 ease-in-out z-30 w-72 flex-shrink-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex flex-col h-full bg-slate-950 border-r border-slate-900 pt-16 lg:pt-0">
          {/* Header Action */}
          <div className="p-4 border-b border-slate-900">
            <button
              onClick={handleLaunchNew}
              className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium rounded-xl flex items-center justify-center gap-2 text-xs font-outfit shadow-md shadow-indigo-500/5 hover:shadow-indigo-500/10 active:transform active:scale-[0.98] transition duration-150"
            >
              <Plus size={14} />
              New Research Session
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <SessionList 
              activeSessionId={sessionId} 
              onSelect={handleSelectSession} 
            />
          </div>
        </div>
      </div>

      {/* 4. Overlay layer for mobile sidebars */}
      {(sidebarOpen || chatOpen) && (
        <div 
          onClick={() => { setSidebarOpen(false); setChatOpen(false); }} 
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm lg:hidden z-20 transition-opacity"
        />
      )}

      {/* 5. Main Workspace Panel (Center) */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Navigation Bar */}
        <header className="h-16 border-b border-slate-900 px-6 flex items-center justify-between flex-shrink-0 bg-slate-950">
          {activeSession && !showCreator ? (
            <div className="flex items-center gap-3 pl-10 lg:pl-0 animate-fadeIn min-w-0 flex-1 mr-4">
              <h2 className="text-sm md:text-base font-bold font-outfit text-slate-100 truncate max-w-[120px] sm:max-w-[180px] md:max-w-[240px]" title={activeSession.company_name || 'Loading...'}>
                {activeSession.company_name }
              </h2>
              {activeSession.website && (
                <a 
                  href={activeSession.website} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-slate-900 border border-slate-850 hover:border-slate-800 hover:bg-slate-850 rounded-lg text-[10px] text-blue-400 hover:text-blue-300 font-medium transition min-w-0 max-w-[120px] sm:max-w-[180px]"
                  title={activeSession.website}
                >
                  <Globe size={11} className="text-slate-500 flex-shrink-0" />
                  <span className="truncate">{activeSession.website.replace(/^https?:\/\/(www\.)?/, '')}</span>
                  <ExternalLink size={9} className="text-slate-500 flex-shrink-0" />
                </a>
              )}
              <div className={`flex items-center gap-1.5 text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-md font-semibold border flex-shrink-0 ${
                activeSession.status === 'done' ? 'bg-emerald-950/20 text-emerald-400 border-emerald-500/20' :
                activeSession.status === 'running' ? 'bg-blue-950/20 text-blue-400 border-blue-500/20' :
                activeSession.status === 'failed' ? 'bg-red-950/20 text-red-400 border-red-500/20' :
                'bg-slate-900 text-slate-400 border-slate-800'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  activeSession.status === 'done' ? 'bg-emerald-500 shadow-md shadow-emerald-500/30' :
                  activeSession.status === 'running' ? 'bg-blue-500 shadow-md shadow-blue-500/30 animate-pulse' :
                  activeSession.status === 'failed' ? 'bg-red-500 shadow-md shadow-red-500/30' :
                  'bg-slate-500'
                }`} />
                <span>
                  {activeSession.status === 'done' ? 'Completed' :
                   activeSession.status === 'running' ? 'In Progress' :
                   activeSession.status === 'failed' ? 'Failed' :
                   'Pending'}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 pl-10 lg:pl-0 text-slate-500 text-xs font-medium min-w-0 flex-1">
              <Compass size={15} className="text-blue-500/80 animate-spin-slow flex-shrink-0" />
              <span className="truncate">Sales Intelligence Workspace</span>
            </div>
          )}

          <div className="flex items-center gap-2 ml-auto flex-shrink-0 whitespace-nowrap">
            <h1 className="font-extrabold text-sm md:text-base font-outfit tracking-wide bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              ZyLabs AI Research Copilot
            </h1>
            <Compass size={18} className="text-blue-500 hidden sm:block flex-shrink-0" />
          </div>
        </header>

        {/* Dynamic Inner Workspace */}
        <main className="flex-1 overflow-hidden relative">
          <Routes>
            <Route 
              path="/" 
              element={
                <div className="h-full flex items-center justify-center p-6 overflow-y-auto">
                  <SessionCreate onSuccess={handleSelectSession} />
                </div>
              } 
            />
            <Route 
              path="/session/:sessionId" 
              element={<SessionDetail />} 
            />
          </Routes>
        </main>
      </div>

      {/* Resizer Handle */}
      {activeSession?.status === 'done' && (
        <div 
          onMouseDown={startResizing}
          className="hidden lg:block w-1 cursor-col-resize hover:bg-blue-500/50 bg-slate-800/50 z-40 transition-colors"
        />
      )}

      {/* 6. Follow-up Q&A Chat Panel (Right) */}
      {activeSession?.status === 'done' && (
        <div 
          style={{ width: typeof window !== 'undefined' && window.innerWidth >= 1024 ? `${chatWidth}px` : '320px' }}
          className={`fixed inset-y-0 right-0 transform lg:relative lg:translate-x-0 transition-transform duration-200 ease-in-out z-30 flex-shrink-0 bg-slate-950 ${
          chatOpen ? 'translate-x-0' : 'translate-x-full'
        }`}>
          <div className="h-full pt-16 lg:pt-0">
            <ChatPanel sessionId={activeSession.id} />
          </div>
        </div>
      )}
      
    </div>
    <ToastContainer />
    </ErrorBoundary>
  );
};

export default App;
