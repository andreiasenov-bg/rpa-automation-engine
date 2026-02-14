import { useState, useRef, useEffect, type ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';
import Tooltip from './Tooltip';
import { useHelpStore } from '../../stores/helpStore';

interface ContextualHelpProps {
  id: string;
  title?: string;
  content: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  size?: number;
  inline?: boolean;
}

export default function ContextualHelp({
  id,
  title,
  content,
  position = 'top',
  size = 16,
  inline = true,
}: ContextualHelpProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const { tooltipsEnabled, hiddenTooltips, hideTooltip } = useHelpStore();

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (!tooltipsEnabled || hiddenTooltips.has(id)) return null;

  const tooltipContent = (
    <div>
      {title && <p className="font-semibold text-slate-900 dark:text-white mb-1">{title}</p>}
      <div className="text-slate-600 dark:text-slate-300 text-xs leading-relaxed">{content}</div>
    </div>
  );

  return (
    <span ref={wrapperRef} className={`relative ${inline ? 'inline-flex' : 'flex'} items-center`}>
      <button
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="p-0.5 rounded-full text-indigo-400 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-300"
        aria-label={`Help: ${title || id}`}
      >
        <HelpCircle size={size} />
      </button>
      <Tooltip
        content={tooltipContent}
        position={position}
        visible={open}
        onClose={() => {
          setOpen(false);
          hideTooltip(id);
        }}
      />
    </span>
  );
}
