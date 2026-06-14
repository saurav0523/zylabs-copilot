import React, { useState, useEffect, useRef } from 'react';
import { useChat } from '../hooks/useChat';
import { Send, MessageSquare, Loader2 } from 'lucide-react';

interface ChatPanelProps {
  sessionId: string;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ sessionId }) => {
  const { chatMessages, sendMessage, loading, error } = useChat(sessionId);
  const [input, setInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const formatTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) {
        return dateStr;
      }
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  const renderChatMessage = (text: string) => {
    if (!text) return null;

    return text.split('\n').map((line, idx) => {
      let trimmed = line.trim();
      
      const parts = trimmed.split('**');
      const nodes = parts.map((part, i) => {
        if (i % 2 === 1) {
          return <strong key={i} className="font-bold text-white">{part}</strong>;
        }
        return part;
      });

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        // Render as bullet point
        const content = nodes.map((n, i) => {
          if (typeof n === 'string') return n.replace(/^[-*]\s*/, '');
          return n;
        });
        return (
          <div key={idx} className="ml-3 flex items-start gap-1.5 py-0.5">
            <span className="text-slate-500 font-bold mt-0.5">•</span>
            <span>{content}</span>
          </div>
        );
      }

      return trimmed ? <div key={idx} className="py-0.5">{nodes}</div> : <div key={idx} className="h-1.5" />;
    });
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const msg = input.trim();
    setInput('');
    await sendMessage(msg);
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  return (
    <div className="flex flex-col h-full bg-slate-950 border-l border-slate-800">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center gap-2 text-slate-200 font-semibold font-outfit">
        <MessageSquare size={18} className="text-blue-500" />
        <span>Ask Copilot</span>
      </div>

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <MessageSquare size={32} className="text-slate-700 mb-2" />
            <p className="text-slate-400 text-xs font-outfit">
              Ask follow-up questions about this sales briefing.
            </p>
            <p className="text-[10px] text-slate-500 mt-1 max-w-[200px]">
              E.g. &quot;What are their major pain points?&quot; or &quot;Outline a discovery strategy.&quot;
            </p>
          </div>
        ) : (
          chatMessages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`flex flex-col max-w-[85%] ${isUser ? 'ml-auto items-end' : 'mr-auto items-start'}`}
              >
                <div
                  className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    isUser
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-slate-900 border border-slate-850 text-slate-200 rounded-bl-none'
                  }`}
                >
                  {renderChatMessage(msg.content)}
                </div>
                <span className="text-[9px] text-slate-500 mt-1 px-1">
                  {formatTime(msg.created_at)}
                </span>
              </div>
            );
          })
        )}
        
        {loading && (
          <div className="flex max-w-[85%] mr-auto items-start">
            <div className="bg-slate-900 border border-slate-850 text-slate-400 px-4 py-3 rounded-2xl rounded-bl-none text-xs flex items-center gap-2">
              <Loader2 size={12} className="animate-spin text-blue-500" />
              Thinking...
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {error && (
        <div className="p-3 bg-red-950/20 border-t border-red-900/30 text-[10px] text-red-400 flex items-center justify-between flex-shrink-0 animate-fadeIn">
          <span>Failed to connect to assistant.</span>
          <button
            type="button"
            onClick={async () => {
              const userMsgs = chatMessages.filter((m) => m.role === 'user');
              if (userMsgs.length > 0) {
                const lastMsg = userMsgs[userMsgs.length - 1];
                await sendMessage(lastMsg.content);
              }
            }}
            className="underline hover:text-red-300 font-semibold"
          >
            Retry sending
          </button>
        </div>
      )}

      {/* Form Input */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-800 bg-slate-950 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a follow-up..."
          disabled={loading}
          className="flex-1 px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition duration-200"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="p-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow transition duration-150 disabled:opacity-50 flex-shrink-0"
        >
          <Send size={14} />
        </button>
      </form>
    </div>
  );
};
export default ChatPanel;
