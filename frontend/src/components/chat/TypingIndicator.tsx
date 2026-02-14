export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-700 rounded-2xl px-4 py-2.5">
        <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-400 animate-bounce [animation-delay:0ms]" />
        <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-400 animate-bounce [animation-delay:150ms]" />
        <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-400 animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}
