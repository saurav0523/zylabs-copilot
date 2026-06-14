import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ShieldAlert, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught component error inside boundary:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-screen h-screen w-screen flex flex-col items-center justify-center bg-slate-950 p-6 text-slate-100 font-sans">
          <div className="w-full max-w-lg glass p-8 rounded-3xl border border-slate-800/80 shadow-2xl text-center space-y-6 animate-fadeIn">
            <div className="mx-auto w-16 h-16 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center text-red-500">
              <ShieldAlert size={36} />
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-bold font-outfit text-slate-100">
                Application Exception
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed max-w-sm mx-auto">
                An unexpected error occurred during user interface rendering. The crash has been logged.
              </p>
            </div>

            {this.state.error && (
              <div className="bg-slate-900 border border-slate-850 rounded-xl p-4 text-left font-mono text-xs text-red-400 overflow-x-auto max-h-36">
                {this.state.error.toString()}
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                onClick={() => window.location.reload()}
                className="flex-1 py-3 px-4 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-xl flex items-center justify-center gap-2 text-xs font-semibold transition"
              >
                <RefreshCw size={14} /> Reload Page
              </button>
              <button
                onClick={this.handleReset}
                className="flex-1 py-3 px-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl flex items-center justify-center gap-2 text-xs transition shadow-md shadow-blue-500/5"
              >
                <Home size={14} /> Return to Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
