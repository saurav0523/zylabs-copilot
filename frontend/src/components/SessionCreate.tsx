import React, { useState } from 'react';
import { useSession } from '../hooks/useSession';
import { Play, Globe, AlignLeft, Building } from 'lucide-react';

interface SessionCreateProps {
  onSuccess: (sessionId: string) => void;
}

export const SessionCreate: React.FC<SessionCreateProps> = ({ onSuccess }) => {
  const { createSession, runSession, loading, error: apiError } = useSession();
  const [companyName, setCompanyName] = useState('');
  const [website, setWebsite] = useState('');
  const [objective, setObjective] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!companyName.trim()) {
      setValidationError('Company name is required.');
      return;
    }
    if (!website.trim()) {
      setValidationError('Website URL is required.');
      return;
    }
    if (!website.startsWith('http://') && !website.startsWith('https://')) {
      setValidationError('Website URL must start with http:// or https://');
      return;
    }
    if (!objective.trim()) {
      setValidationError('Meeting objective is required.');
      return;
    }

    try {
      const session = await createSession(companyName, website, objective);
      await runSession(session.id);
      onSuccess(session.id);
    } catch (err: any) {
      console.error('Failed to create/run session', err);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto glass p-8 rounded-2xl shadow-xl border border-slate-800 animate-fadeIn">
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-bold font-outfit bg-gradient-to-r from-blue-400 via-indigo-300 to-indigo-500 bg-clip-text text-transparent">
          Start Research Copilot
        </h2>
        <p className="text-slate-400 mt-2 text-sm">
          Provide company details to initiate real-time research, analysis, and briefing generation.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="companyName" className="block text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
            <Building size={16} className="text-blue-400" />
            Company Name
          </label>
          <input
            id="companyName"
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g. Acme Corp"
            className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200"
          />
        </div>

        <div>
          <label htmlFor="website" className="block text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
            <Globe size={16} className="text-blue-400" />
            Company Website
          </label>
          <input
            id="website"
            type="text"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="e.g. https://acmecorp.com"
            className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200"
          />
        </div>

        <div>
          <label htmlFor="objective" className="block text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
            <AlignLeft size={16} className="text-blue-400" />
            Meeting Objective
          </label>
          <textarea
            id="objective"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="e.g. Pitching automated CRM migrations to the VP of Sales."
            rows={4}
            className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200 resize-none"
          />
        </div>

        {validationError && (
          <div className="p-4 bg-red-950/40 border border-red-900/40 rounded-xl text-red-400 text-sm">
            {validationError}
          </div>
        )}

        {apiError && (
          <div className="p-4 bg-red-950/40 border border-red-900/40 rounded-xl text-red-400 text-sm">
            {apiError}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium rounded-xl shadow-lg hover:shadow-indigo-500/20 active:transform active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-base font-outfit"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
              Initializing Workflow...
            </>
          ) : (
            <>
              <Play size={18} fill="white" />
              Launch Research Workflow
            </>
          )}
        </button>
      </form>
    </div>
  );
};
export default SessionCreate;
