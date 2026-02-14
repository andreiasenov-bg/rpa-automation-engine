import { useState, useRef, useEffect } from 'react';
import { X, Trash2, Send, Bot, Sparkles } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { suggestedQuestions } from '../../data/helpContent';
import { useLocale } from '../../i18n';
import ChatMessage from './ChatMessage';
import TypingIndicator from './TypingIndicator';

export default function ChatPanel() {
  const { messages, isLoading, closeChat, sendMessage, clearConversation, pageContext } = useChatStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { locale } = useLocale();
  const lang = locale as 'en' | 'bg';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput('');
    sendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = suggestedQuestions[pageContext] || suggestedQuestions['/'] || [];
  const showSuggestions = messages.length === 0;

  return (
    <div className="fixed bottom-24 right-6 w-96 max-h-[520px] bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col z-[9998] animate-[slideUp_0.2s_ease-out]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl">
        <div className="flex items-center gap-2">
          <Bot size={20} className="text-white" />
          <span className="font-semibold text-white">
            {lang === 'bg' ? 'AI Помощник' : 'AI Assistant'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearConversation}
            className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10"
            title={lang === 'bg' ? 'Изчисти разговора' : 'Clear conversation'}
          >
            <Trash2 size={16} />
          </button>
          <button
            onClick={closeChat}
            className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-3 min-h-[280px] max-h-[360px]">
        {showSuggestions ? (
          <div className="px-4 py-6 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 flex items-center justify-center">
              <Sparkles size={24} className="text-indigo-500" />
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-sm mb-4">
              {lang === 'bg'
                ? 'Здравейте! Как мога да ви помогна?'
                : 'Hi! How can I help you?'}
            </p>
            <div className="space-y-2">
              {suggestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q[lang])}
                  className="block w-full text-left px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-sm text-slate-600 dark:text-slate-300 hover:text-indigo-700 dark:hover:text-indigo-300 border border-slate-200 dark:border-slate-600 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors"
                >
                  {q[lang]}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 dark:border-slate-700 p-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={lang === 'bg' ? 'Напишете въпрос...' : 'Type a question...'}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 px-3 py-2 text-sm text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:focus:ring-indigo-600 max-h-20"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-600 text-white transition-colors"
            aria-label="Send"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
