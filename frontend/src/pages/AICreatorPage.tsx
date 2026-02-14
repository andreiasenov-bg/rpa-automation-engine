import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Search,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Loader2,
  Wand2,
  Tag,
  Clock,
  BarChart3,
  ExternalLink,
} from 'lucide-react';
import { templatesApi, type TemplateSummary } from '../api/templates';

/* ─── Types ────────────────────────────────────────────────── */
type CreationStatus = 'idle' | 'matching' | 'matched' | 'creating' | 'success' | 'error';

interface MatchedTemplate extends TemplateSummary {
  score: number;
}

/* ─── Scoring logic (mirrors backend match_template) ──────── */
function scoreTemplate(tpl: TemplateSummary, query: string): number {
  const q = query.toLowerCase();
  let score = 0;

  // Name words (3 points each if word > 3 chars)
  for (const word of tpl.name.toLowerCase().split(/\s+/)) {
    if (word.length > 3 && q.includes(word)) score += 3;
  }

  // Tags (2 points each)
  for (const tag of tpl.tags) {
    if (q.includes(tag.toLowerCase())) score += 2;
  }

  // Category (1 point)
  if (q.includes(tpl.category.replace(/-/g, ' '))) score += 1;

  // Description words (1 point each if word > 4 chars)
  for (const word of tpl.description.toLowerCase().split(/\s+/)) {
    if (word.length > 4 && q.includes(word)) score += 1;
  }

  return score;
}

/* ─── Component ───────────────────────────────────────────── */
export default function AICreatorPage() {
  const navigate = useNavigate();
  const [description, setDescription] = useState('');
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [matches, setMatches] = useState<MatchedTemplate[]>([]);
  const [status, setStatus] = useState<CreationStatus>('idle');
  const [createdWorkflow, setCreatedWorkflow] = useState<{ id: string; name: string } | null>(null);
  const [error, setError] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<MatchedTemplate | null>(null);

  // Load templates once
  useEffect(() => {
    templatesApi.list().then((res) => setTemplates(res.templates)).catch(() => {});
  }, []);

  // Match templates as user types
  const updateMatches = useCallback(
    (text: string) => {
      if (text.trim().length < 3) {
        setMatches([]);
        setStatus('idle');
        return;
      }

      setStatus('matching');

      const scored = templates
        .map((tpl) => ({ ...tpl, score: scoreTemplate(tpl, text) }))
        .filter((t) => t.score >= 3)
        .sort((a, b) => b.score - a.score)
        .slice(0, 5);

      setMatches(scored);
      setStatus(scored.length > 0 ? 'matched' : 'idle');
      if (scored.length > 0) {
        setSelectedTemplate(scored[0]);
      } else {
        setSelectedTemplate(null);
      }
    },
    [templates],
  );

  useEffect(() => {
    const timeout = setTimeout(() => updateMatches(description), 300);
    return () => clearTimeout(timeout);
  }, [description, updateMatches]);

  // Create workflow from template
  const handleCreate = async (tpl: MatchedTemplate) => {
    setStatus('creating');
    setError('');
    setSelectedTemplate(tpl);

    try {
      const result = await templatesApi.instantiate(tpl.id, tpl.name, tpl.description);
      setCreatedWorkflow({ id: result.workflow_id, name: result.name });
      setStatus('success');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create workflow';
      setError(msg);
      setStatus('error');
    }
  };

  const handleReset = () => {
    setDescription('');
    setMatches([]);
    setStatus('idle');
    setCreatedWorkflow(null);
    setError('');
    setSelectedTemplate(null);
  };

  /* ─── Status Banner ─────────────────────────────────────── */
  const renderStatusBanner = () => {
    if (status === 'creating') {
      return (
        <div className="flex items-center gap-3 p-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-xl animate-pulse">
          <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
          <div>
            <p className="font-medium text-indigo-800 dark:text-indigo-200">
              Creating workflow from "{selectedTemplate?.name}"...
            </p>
            <p className="text-sm text-indigo-600 dark:text-indigo-400">
              Configuring {selectedTemplate?.step_count} steps automatically
            </p>
          </div>
        </div>
      );
    }

    if (status === 'success' && createdWorkflow) {
      return (
        <div className="flex items-center justify-between p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-xl">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
            <div>
              <p className="font-semibold text-emerald-800 dark:text-emerald-200">
                Workflow "{createdWorkflow.name}" created!
              </p>
              <p className="text-sm text-emerald-600 dark:text-emerald-400">
                {selectedTemplate?.step_count} steps configured. Ready to review and publish.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate(`/workflows/${createdWorkflow.id}/edit`)}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
            >
              <ExternalLink size={14} />
              Open & Edit
            </button>
            <button
              onClick={() => navigate('/workflows')}
              className="flex items-center gap-1.5 px-4 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
            >
              All Workflows
            </button>
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-4 py-2 text-slate-500 dark:text-slate-400 text-sm hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
            >
              Create Another
            </button>
          </div>
        </div>
      );
    }

    if (status === 'error') {
      return (
        <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl">
          <div className="flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="font-medium text-red-800 dark:text-red-200">Creation failed</p>
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          </div>
          <button
            onClick={() => { setStatus('matched'); setError(''); }}
            className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      );
    }

    return null;
  };

  /* ─── Render ────────────────────────────────────────────── */
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl">
          <Wand2 className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">AI Workflow Creator</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Describe what you need — we'll find the right template and create it instantly
          </p>
        </div>
      </div>

      {/* Input Area */}
      <div className="relative mb-6">
        <div className="absolute left-4 top-4 pointer-events-none">
          <Search className="w-5 h-5 text-slate-400" />
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the workflow you need... e.g. 'Track top 10000 best-selling products on Amazon.de daily with auto-restart and error reporting'"
          className="w-full pl-12 pr-4 py-4 min-h-[120px] bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 text-base leading-relaxed focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none resize-y transition-all"
          disabled={status === 'creating' || status === 'success'}
          autoFocus
        />
        {description.length > 0 && status !== 'success' && (
          <button
            onClick={handleReset}
            className="absolute right-3 top-3 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded"
          >
            <XCircle size={16} />
          </button>
        )}
      </div>

      {/* Status Banner */}
      {renderStatusBanner()}

      {/* Matched Templates */}
      {matches.length > 0 && status !== 'success' && status !== 'creating' && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Sparkles size={14} />
            Matching Templates ({matches.length})
          </h2>
          <div className="space-y-3">
            {matches.map((tpl) => (
              <div
                key={tpl.id}
                className={`group relative p-4 bg-white dark:bg-slate-800 border-2 rounded-xl transition-all cursor-pointer hover:shadow-md ${
                  selectedTemplate?.id === tpl.id
                    ? 'border-indigo-400 dark:border-indigo-500 shadow-sm'
                    : 'border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600'
                }`}
                onClick={() => setSelectedTemplate(tpl)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xl">{tpl.icon}</span>
                      <h3 className="font-semibold text-slate-900 dark:text-white truncate">
                        {tpl.name}
                      </h3>
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-medium rounded-full">
                        <BarChart3 size={10} />
                        {Math.min(Math.round((tpl.score / 15) * 100), 99)}% match
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2 mb-2">
                      {tpl.description}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-500">
                      <span className="flex items-center gap-1">
                        <Clock size={11} />
                        {tpl.step_count} steps
                      </span>
                      <span className="capitalize">{tpl.difficulty}</span>
                      <span>{tpl.estimated_duration}</span>
                      <div className="flex items-center gap-1">
                        <Tag size={11} />
                        {tpl.tags.slice(0, 3).join(', ')}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCreate(tpl);
                    }}
                    className="flex items-center gap-1.5 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 active:bg-indigo-800 transition-colors whitespace-nowrap shadow-sm"
                  >
                    <Sparkles size={14} />
                    Create
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state when no matches */}
      {description.trim().length >= 3 && matches.length === 0 && status === 'idle' && (
        <div className="mt-6 text-center py-8 px-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
          <Search className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <p className="text-slate-600 dark:text-slate-400 font-medium">No matching templates found</p>
          <p className="text-sm text-slate-500 dark:text-slate-500 mt-1">
            Try different keywords or{' '}
            <button
              onClick={() => navigate('/templates')}
              className="text-indigo-500 hover:text-indigo-600 underline"
            >
              browse all templates
            </button>
          </p>
        </div>
      )}

      {/* Initial state hint */}
      {description.trim().length < 3 && status === 'idle' && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
            Try describing:
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              'Track best-selling products on Amazon.de daily',
              'Monitor competitor prices automatically',
              'Scrape data from websites and save to Excel',
              'Send automated email reports with analytics',
              'Sync inventory across Shopify and Amazon',
              'Monitor website uptime and alert on Slack',
            ].map((example) => (
              <button
                key={example}
                onClick={() => setDescription(example)}
                className="flex items-center gap-2 p-3 text-left text-sm text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all"
              >
                <ArrowRight size={14} className="text-slate-400 flex-shrink-0" />
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
