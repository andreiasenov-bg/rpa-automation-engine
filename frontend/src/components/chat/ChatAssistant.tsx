import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { MessageCircle, X } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import ChatPanel from './ChatPanel';

export default function ChatAssistant() {
  const { isOpen, toggleChat, setPageContext, messages } = useChatStore();
  const location = useLocation();

  useEffect(() => {
    setPageContext(location.pathname);
  }, [location.pathname]);

  return (
    <>
      {/* Chat Panel */}
      {isOpen && <ChatPanel />}

      {/* Floating Button */}
      <button
        onClick={toggleChat}
        className={`fixed bottom-6 right-6 z-[9999] w-14 h-14 rounded-full shadow-xl flex items-center justify-center transition-all duration-200 ${
          isOpen
            ? 'bg-slate-600 hover:bg-slate-700 rotate-0'
            : 'bg-indigo-600 hover:bg-indigo-700 hover:scale-105'
        }`}
        aria-label={isOpen ? 'Close chat' : 'Open AI Assistant'}
      >
        {isOpen ? (
          <X size={22} className="text-white" />
        ) : (
          <>
            <MessageCircle size={22} className="text-white" />
            {messages.length === 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-purple-500 rounded-full animate-ping" />
            )}
          </>
        )}
      </button>
    </>
  );
}
