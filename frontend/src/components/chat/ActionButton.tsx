import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Play,
  RotateCcw,
  XCircle,
  Eye,
  Plus,
  Loader2,
  Check,
  AlertTriangle,
} from 'lucide-react';
import type { ChatAction } from '../../stores/chatStore';
import { chatApi } from '../../api/chat';
import { useChatStore } from '../../stores/chatStore';

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  ArrowRight,
  Play,
  RotateCcw,
  XCircle,
  Eye,
  Plus,
};

type ButtonStatus = 'idle' | 'loading' | 'success' | 'error';

interface Props {
  action: ChatAction;
  conversationId: string;
}

export default function ActionButton({ action, conversationId }: Props) {
  const [status, setStatus] = useState<ButtonStatus>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();
  const addMessage = useChatStore((s) => s.addSystemMessage);

  const IconComponent = ICON_MAP[action.icon] || ArrowRight;

  const handleClick = async () => {
    if (status === 'loading' || status === 'success') return;

    // Confirmation dialog if required
    if (action.confirm) {
      const ok = window.confirm(`Are you sure you want to: ${action.label}?`);
      if (!ok) return;
    }

    // Navigate actions handled client-side
    if (action.type === 'navigate') {
      const path = action.params.path as string;
      if (path) {
        navigate(path);
        useChatStore.getState().closeChat();
      }
      return;
    }

    // All other actions go through the backend
    setStatus('loading');
    setErrorMsg('');

    try {
      const result = await chatApi.executeAction(conversationId, action);

      if (result.success) {
        setStatus('success');
        if (result.message) {
          addMessage(result.message, false);
        }
        // Navigate if redirect provided
        if (result.redirect) {
          setTimeout(() => {
            navigate(result.redirect!);
            useChatStore.getState().closeChat();
          }, 800);
        }
      } else {
        setStatus('error');
        setErrorMsg(result.message || 'Action failed');
        addMessage(result.message || 'Action failed', true);
      }
    } catch (err: any) {
      setStatus('error');
      const msg = err.response?.data?.detail || 'Action failed';
      setErrorMsg(msg);
      addMessage(msg, true);
    }
  };

  const statusStyles: Record<ButtonStatus, string> = {
    idle: 'bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300',
    loading: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-300 dark:border-indigo-600 text-indigo-600 dark:text-indigo-400 cursor-wait',
    success: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-600 text-emerald-700 dark:text-emerald-400',
    error: 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-600 text-red-700 dark:text-red-400',
  };

  return (
    <div className="inline-flex flex-col">
      <button
        onClick={handleClick}
        disabled={status === 'loading' || status === 'success'}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all duration-150 ${statusStyles[status]}`}
        title={errorMsg || action.label}
      >
        {status === 'loading' ? (
          <Loader2 size={13} className="animate-spin" />
        ) : status === 'success' ? (
          <Check size={13} />
        ) : status === 'error' ? (
          <AlertTriangle size={13} />
        ) : (
          <IconComponent size={13} />
        )}
        <span>{action.label}</span>
      </button>
      {status === 'error' && errorMsg && (
        <span className="text-[10px] text-red-500 dark:text-red-400 mt-0.5 px-1">{errorMsg}</span>
      )}
    </div>
  );
}
