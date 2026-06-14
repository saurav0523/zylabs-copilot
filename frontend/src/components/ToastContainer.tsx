import React, { useEffect } from 'react';
import { useSessionStore, type ToastMessage } from '../store/sessionStore';
import { AlertCircle, CheckCircle2, Info, X, RotateCcw } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const toasts = useSessionStore((state) => state.toasts);
  const removeToast = useSessionStore((state) => state.removeToast);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
};

interface ToastItemProps {
  toast: ToastMessage;
  onRemove: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  useEffect(() => {
    // Only auto-remove if there is no retry action
    if (!toast.retryAction) {
      const timer = setTimeout(() => {
        onRemove(toast.id);
      }, 6000); // 6 seconds auto-dismiss
      return () => clearTimeout(timer);
    }
  }, [toast, onRemove]);

  const getStyles = () => {
    switch (toast.type) {
      case 'success':
        return {
          bg: 'bg-emerald-950/80 border-emerald-900/40 text-emerald-300',
          icon: <CheckCircle2 size={16} className="text-emerald-400 mt-0.5" />
        };
      case 'info':
        return {
          bg: 'bg-blue-950/80 border-blue-900/40 text-blue-300',
          icon: <Info size={16} className="text-blue-400 mt-0.5" />
        };
      case 'error':
      default:
        return {
          bg: 'bg-red-950/80 border-red-900/40 text-red-350',
          icon: <AlertCircle size={16} className="text-red-400 mt-0.5" />
        };
    }
  };

  const { bg, icon } = getStyles();

  return (
    <div
      className={`p-4 rounded-xl border backdrop-blur-md shadow-lg flex items-start gap-3 pointer-events-auto animate-fadeIn ${bg}`}
    >
      <div className="flex-shrink-0">{icon}</div>
      <div className="flex-1 text-xs leading-relaxed break-words font-medium">
        {toast.message}
        
        {toast.retryAction && (
          <div className="mt-2 text-left">
            <button
              onClick={async () => {
                onRemove(toast.id);
                if (toast.retryAction) {
                  try {
                    await toast.retryAction();
                  } catch (err) {
                    console.error('Toast retry action failed:', err);
                  }
                }
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-white/10 hover:bg-white/15 active:bg-white/5 border border-white/5 rounded-lg text-[10px] font-bold text-white transition font-outfit"
            >
              <RotateCcw size={10} /> Retry Action
            </button>
          </div>
        )}
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-slate-400 hover:text-white transition flex-shrink-0 mt-0.5"
      >
        <X size={14} />
      </button>
    </div>
  );
};

export default ToastContainer;
