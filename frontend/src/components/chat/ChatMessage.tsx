import { Bot, User, AlertCircle } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../stores/chatStore';
import ActionButton from './ActionButton';
import { useChatStore } from '../../stores/chatStore';

interface Props {
  message: ChatMessageType;
}

function simpleMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-slate-200 dark:bg-slate-600 px-1 py-0.5 rounded text-xs">$1</code>')
    .replace(/\n/g, '<br/>');
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const conversationId = useChatStore((s) => s.conversationId);

  // System messages (action results)
  if (isSystem) {
    return (
      <div className="flex justify-center px-3 py-1">
        <div
          className={`text-xs px-3 py-1.5 rounded-full ${
            message.error
              ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
              : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
          }`}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-2 px-3 py-1.5 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400'
            : 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400'
        }`}
      >
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>

      {/* Bubble */}
      <div className="max-w-[80%]">
        <div
          className={`rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'bg-indigo-600 text-white rounded-br-md'
              : message.error
              ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 rounded-bl-md'
              : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-bl-md'
          }`}
        >
          {message.error && (
            <div className="flex items-center gap-1 mb-1">
              <AlertCircle size={12} />
              <span className="text-xs font-medium">Error</span>
            </div>
          )}
          <div dangerouslySetInnerHTML={{ __html: simpleMarkdown(message.content) }} />
          <div
            className={`text-[10px] mt-1 ${
              isUser ? 'text-indigo-200' : 'text-slate-400 dark:text-slate-500'
            }`}
          >
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>

        {/* Action Buttons */}
        {!isUser && message.actions && message.actions.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2 ml-1">
            {message.actions.map((action, i) => (
              <ActionButton key={i} action={action} conversationId={conversationId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
