import { useState, useRef, useEffect, type ReactNode } from 'react';
import { X } from 'lucide-react';

type Position = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: ReactNode;
  position?: Position;
  visible: boolean;
  onClose?: () => void;
  className?: string;
}

export default function Tooltip({ content, position = 'top', visible, onClose, className = '' }: TooltipProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!visible || !onClose) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [visible, onClose]);

  if (!visible) return null;

  const posClasses: Record<Position, string> = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  const arrowClasses: Record<Position, string> = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-slate-200 dark:border-t-slate-600 border-l-transparent border-r-transparent border-b-transparent',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-slate-200 dark:border-b-slate-600 border-l-transparent border-r-transparent border-t-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-slate-200 dark:border-l-slate-600 border-t-transparent border-b-transparent border-r-transparent',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-slate-200 dark:border-r-slate-600 border-t-transparent border-b-transparent border-l-transparent',
  };

  return (
    <div
      ref={ref}
      role="tooltip"
      className={`absolute z-50 ${posClasses[position]} w-72 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg shadow-lg p-3 text-sm text-slate-700 dark:text-slate-200 animate-[fadeIn_0.15s_ease-out] ${className}`}
    >
      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-1.5 right-1.5 p-0.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400"
          aria-label="Close"
        >
          <X size={14} />
        </button>
      )}
      <div className="pr-4">{content}</div>
      <div className={`absolute w-0 h-0 border-[6px] ${arrowClasses[position]}`} />
    </div>
  );
}
