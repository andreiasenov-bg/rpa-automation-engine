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
  Bot,
  Zap,
  Globe,
  FileText,
  Send,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Play,
  Eye,
} from 'lucide-react';
import { templatesApi, type TemplateSummary } from '../api/templates';
import { workflowApi } from '../api/workflows';
import client from '../api/client';

/* ─── Types ────────────────────────────────────────────────── */
type Mode = 'ai' | 'templates';
type AIStatus = 'idle' | 'generating' | 'generated' | 'creating' | 'success' | 'error';

interface GeneratedWorkflow {
  name: string;
  description: string;
  steps: any[];
}

interface MatchedTemplate extends TemplateSummary {
  score: number;
}

/* ─── Scoring logic ──────────────────────────────────────── */
function scoreTemplate(tpl: TemplateSummary, query: string): number {
  const q = query.toLowerCase();
  let score = 0;
  for (const word of tpl.name.toLowerCase().split(/\s+/)) {
    if (word.length > 3 && q.includes(word)) score += 3;
  }
  for (const tag of tpl.tags) {
    if (q.includes(tag.toLowerCase())) score += 2;
  }
  if (q.includes(tpl.category.replace(/-/g, ' '))) score += 1;
  for (const word of tpl.description.toLowerCase().split(/\s+/)) {
    if (word.length > 4 && q.includes(word)) score += 1;
  }
  return score;
}

/* ─── Component ───────────────────────────────────────────── */
export default function AICreatorPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('ai');
  const [description, setDescription] = useState('');

  // AI mode state
  const [aiStatus, setAiStatus] = useState<AIStatus>('idle');
  const [generatedWorkflow, setGeneratedWorkflow] = useState<GeneratedWorkflow | null>(null);
  const [createdWorkflowId, setCreatedWorkflowId] = useState<string | null>(null);
  const [aiError, setAiError] = useState('');
  const [showSteps, setShowSteps] = useState(false);

  // Template mode state
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [matches, setMatches] = useState<MatchedTemplate[]>([]);
  const [templateStatus, setTemplateStatus] = useState<'idle' | 'creating' | 'success' | 'error'>('idle');
  const [templateError, setTemplateError] = useState('');
  const [createdFromTemplate, setCreatedFromTemplate] = useState<{ id: string; name: string } | null>(null);

  // Load templates
  useEffect(() => {
    templatesApi.list().then((res) => setTemplates(res.templates)).catch(() => {});
  }, []);

  // Match templates as user types (only in template mode)
  useEffect(() => {
    if (mode !== 'templates' || description.trim().length < 3) {
      setMatches([]);
      return;
    }
    const timeout = setTimeout(() => {
      const scored = templates
        .map((tpl) => ({ ...tpl, score: scoreTemplate(tpl, description) }))
        .filter((t) => t.score >= 2)
        .sort((a, b) => b.score - a.score)
        .slice(0, 8);
      setMatches(scored);
    }, 300);
    return () => clearTimeout(timeout);
  }, [description, templates, mode]);

  /* ─── AI Generate ───────────────────────────────────────── */
  const handleAIGenerate = async () => {
    if (!description.trim()) return;
    setAiStatus('generating');
    setAiError('');
    setGeneratedWorkflow(null);

    try {
      const { data } = await client.post('/ai/generate-workflow', {
        description: description.trim(),
        language: /[а-яА-Я]/.test(description) ? 'bg' : 'en',
      }, { timeout: 120000 });

      if (data.success && data.workflow) {
        setGeneratedWorkflow(data.workflow);
        setAiStatus('generated');
      } else {
        setAiError(data.error || 'AI could not generate a valid workflow');
        setAiStatus('error');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to generate workflow';
      setAiError(msg);
      setAiStatus('error');
    }
  };

  /* ─── Create from AI result ─────────────────────────────── */
  const handleCreateFromAI = async () => {
    if (!generatedWorkflow) return;
    setAiStatus('creating');

    try {
      const result = await workflowApi.create({
        name: generatedWorkflow.name,
        description: generatedWorkflow.description,
        definition: { steps: generatedWorkflow.steps },
      });
      setCreatedWorkflowId(result.id);
      setAiStatus('success');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create workflow';
      setAiError(msg);
      setAiStatus('error');
    }
  };

  /* ─── Create from template ─────────────────────────────── */
  const handleCreateFromTemplate = async (tpl: MatchedTemplate) => {
    setTemplateStatus('creating');
    setTemplateError('');

    try {
      const result = await templatesApi.instantiate(tpl.id, tpl.name, tpl.description);
      setCreatedFromTemplate({ id: result.workflow_id, name: result.name });
      setTemplateStatus('success');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create workflow';
      setTemplateError(msg);
      setTemplateStatus('error');
    }
  };

  /* ─── Reset ────────────────────────────────────────────── */
  const handleReset = () => {
    setDescription('');
    setAiStatus('idle');
    setGeneratedWorkflow(null);
    setCreatedWorkflowId(null);
    setAiError('');
    setShowSteps(false);
    setTemplateStatus('idle');
    setTemplateError('');
    setCreatedFromTemplate(null);
    setMatches([]);
  };

  const stepTypeIcons: Record<string, string> = {
    web_scrape: '🕷️', http_request: '🌐', custom_script: '📜', data_transform: '🔄',
    email_send: '✉️', file_write: '💾', database_query: '🗄️', condition: '🔀',
    loop: '🔁', delay: '⏱️', ai_ask: '🤖', ai_analyze: '🧠', ai_summarize: '📝',
    form_fill: '📋', browser_navigate: '🧭', browser_click: '👆', browser_extract: '📊',
  };

  /* ─── Render ────────────────────────────────────────────── */
  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl">
            <Wand2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">AI Workflow Creator</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Describe what you need and AI will design the workflow for you
            </p>
          </div>
        </div>
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl mb-6 w-fit">
        <button
          onClick={() => { setMode('ai'); handleReset(); }}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
            mode === 'ai'
              ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <Bot size={16} />
          AI Generate
        </button>
        <button
          onClick={() => { setMode('templates'); handleReset(); }}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
            mode === 'templates'
              ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <FileText size={16} />
          From Template
        </button>
      </div>

      {/* Input Area */}
      <div className="relative mb-6">
        <div className="absolute left-4 top-4 pointer-events-none">
          {mode === 'ai' ? <Bot className="w-5 h-5 text-indigo-400" /> : <Search className="w-5 h-5 text-slate-400" />}
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={
            mode === 'ai'
              ? 'Describe in detail what your workflow should do...\ne.g. "Scrape the top 100 products from Amazon.de Best Sellers in Electronics, extract title, price, rating, and ASIN, then save to CSV and send a summary email"'
              : 'Search templates... e.g. "track product prices" or "monitor website uptime"'
          }
          className="w-full pl-12 pr-4 py-4 min-h-[140px] bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 text-base leading-relaxed focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none resize-y transition-all"
          disabled={aiStatus === 'generating' || aiStatus === 'creating' || aiStatus === 'success' || templateStatus === 'creating' || templateStatus === 'success'}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && mode === 'ai' && description.trim()) {
              handleAIGenerate();
            }
          }}
        />
        {description.length > 0 && aiStatus !== 'success' && templateStatus !== 'success' && (
          <button
            onClick={handleReset}
            className="absolute right-3 top-3 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded"
          >
            <XCircle size={16} />
          </button>
        )}
      </div>

      {/* AI Generate Button */}
      {mode === 'ai' && aiStatus === 'idle' && description.trim().length > 10 && (
        <button
          onClick={handleAIGenerate}
          className="flex items-center gap-2 px-6 py-3 mb-6 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl text-base font-semibold hover:from-indigo-700 hover:to-purple-700 active:from-indigo-800 active:to-purple-800 transition-all shadow-lg shadow-indigo-500/25"
        >
          <Sparkles size={18} />
          Generate Workflow with AI
          <span className="text-xs opacity-75 ml-1">Ctrl+Enter</span>
        </button>
      )}

      {/* ─── AI Mode Status ─── */}
      {mode === 'ai' && (
        <>
          {/* Generating */}
          {aiStatus === 'generating' && (
            <div className="flex items-center gap-3 p-5 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-xl mb-6">
              <div className="relative">
                <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
                <Sparkles className="w-3 h-3 text-purple-500 absolute -top-1 -right-1 animate-pulse" />
              </div>
              <div>
                <p className="font-medium text-indigo-800 dark:text-indigo-200">AI is designing your workflow...</p>
                <p className="text-sm text-indigo-600 dark:text-indigo-400">Analyzing requirements and generating steps</p>
              </div>
            </div>
          )}

          {/* Generated — Preview */}
          {aiStatus === 'generated' && generatedWorkflow && (
            <div className="mb-6 space-y-4">
              <div className="p-5 bg-white dark:bg-slate-800 border-2 border-indigo-200 dark:border-indigo-700 rounded-xl">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="w-5 h-5 text-indigo-500" />
                      <h3 className="text-lg font-bold text-slate-900 dark:text-white">{generatedWorkflow.name}</h3>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{generatedWorkflow.description}</p>
                  </div>
                  <span className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-semibold rounded-full">
                    {generatedWorkflow.steps.length} steps
                  </span>
                </div>

                {/* Steps Preview */}
                <button
                  onClick={() => setShowSteps(!showSteps)}
                  className="flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 mb-3"
                >
                  {showSteps ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showSteps ? 'Hide' : 'Preview'} Steps
                </button>

                {showSteps && (
                  <div className="space-y-2 mb-4">
                    {generatedWorkflow.steps.map((step: any, i: number) => (
                      <div key={step.id || i} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                        <span className="text-lg">{stepTypeIcons[step.type] || '⚙️'}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                            {step.name || step.id}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">{step.type}</p>
                        </div>
                        <span className="text-xs text-slate-400 dark:text-slate-500">#{i + 1}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={handleCreateFromAI}
                    className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
                  >
                    <CheckCircle2 size={16} />
                    Create Workflow
                  </button>
                  <button
                    onClick={handleAIGenerate}
                    className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
                  >
                    <RefreshCw size={14} />
                    Regenerate
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-2 px-4 py-2.5 text-slate-500 dark:text-slate-400 text-sm hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                  >
                    Start Over
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Creating */}
          {aiStatus === 'creating' && (
            <div className="flex items-center gap-3 p-5 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-xl mb-6 animate-pulse">
              <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
              <p className="font-medium text-indigo-800 dark:text-indigo-200">Creating workflow...</p>
            </div>
          )}

          {/* Success */}
          {aiStatus === 'success' && createdWorkflowId && (
            <div className="p-5 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-xl mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                  <div>
                    <p className="font-semibold text-emerald-800 dark:text-emerald-200">
                      Workflow "{generatedWorkflow?.name}" created successfully!
                    </p>
                    <p className="text-sm text-emerald-600 dark:text-emerald-400">
                      {generatedWorkflow?.steps.length} steps configured. Open it to review, edit, and publish.
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/workflows/${createdWorkflowId}/edit`)}
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
                    className="px-3 py-2 text-slate-500 dark:text-slate-400 text-sm hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                  >
                    Create Another
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {aiStatus === 'error' && (
            <div className="p-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <XCircle className="w-5 h-5 text-red-500" />
                  <div>
                    <p className="font-medium text-red-800 dark:text-red-200">Generation failed</p>
                    <p className="text-sm text-red-600 dark:text-red-400">{aiError}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleAIGenerate}
                    className="px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-lg transition-colors font-medium"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={handleReset}
                    className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                  >
                    Reset
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ─── Template Mode ─── */}
      {mode === 'templates' && (
        <>
          {/* Template Success */}
          {templateStatus === 'success' && createdFromTemplate && (
            <div className="p-5 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-xl mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                  <div>
                    <p className="font-semibold text-emerald-800 dark:text-emerald-200">
                      Workflow "{createdFromTemplate.name}" created!
                    </p>
                    <p className="text-sm text-emerald-600 dark:text-emerald-400">Ready to review and publish.</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/workflows/${createdFromTemplate.id}/edit`)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
                  >
                    <ExternalLink size={14} />
                    Open & Edit
                  </button>
                  <button onClick={handleReset} className="px-3 py-2 text-sm text-slate-500">
                    Create Another
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Template Error */}
          {templateStatus === 'error' && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl mb-6">
              <div className="flex items-center gap-3">
                <XCircle className="w-5 h-5 text-red-500" />
                <p className="text-sm text-red-600 dark:text-red-400">{templateError}</p>
              </div>
            </div>
          )}

          {/* Matched Templates */}
          {matches.length > 0 && templateStatus !== 'success' && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Sparkles size={14} />
                Matching Templates ({matches.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {matches.map((tpl) => (
                  <div
                    key={tpl.id}
                    className="group p-4 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-md transition-all"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{tpl.icon}</span>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-sm">{tpl.name}</h3>
                      </div>
                      <span className="px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-medium rounded-full whitespace-nowrap">
                        {Math.min(Math.round((tpl.score / 15) * 100), 99)}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2 mb-3">{tpl.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-500">
                        <span>{tpl.step_count} steps</span>
                        <span className="capitalize">{tpl.difficulty}</span>
                      </div>
                      <button
                        onClick={() => handleCreateFromTemplate(tpl)}
                        disabled={templateStatus === 'creating'}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50"
                      >
                        {templateStatus === 'creating' ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                        Use Template
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No matches */}
          {description.trim().length >= 3 && matches.length === 0 && templateStatus === 'idle' && (
            <div className="text-center py-8 px-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 mb-6">
              <Search className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="text-slate-600 dark:text-slate-400 font-medium">No matching templates</p>
              <p className="text-sm text-slate-500 dark:text-slate-500 mt-1">
                Try the <button onClick={() => setMode('ai')} className="text-indigo-500 hover:text-indigo-600 underline font-medium">AI Generate</button> mode to create a custom workflow
              </p>
            </div>
          )}
        </>
      )}

      {/* ─── Quick Examples ─── */}
      {description.trim().length < 3 && aiStatus === 'idle' && templateStatus === 'idle' && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
            {mode === 'ai' ? 'Try these examples:' : 'Try searching for:'}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(mode === 'ai' ? [
              'Scrape Amazon.de Best Sellers top 100 products in Electronics, extract title, price, rating, ASIN and save to CSV',
              'Monitor my website uptime every 5 minutes, check response time, and send Slack alert if it goes down',
              'Extract all email addresses from a list of web pages and save to a spreadsheet',
              'Track competitor prices daily, compare with our prices, and alert me if they change by more than 5%',
              'Download daily exchange rates from an API, calculate trends, and send a morning report email',
              'Check inventory levels via API, find items below threshold, and auto-generate purchase orders',
            ] : [
              'Track best-selling products on Amazon.de daily',
              'Monitor competitor prices automatically',
              'Scrape data from websites and save to Excel',
              'Send automated email reports with analytics',
              'Sync inventory across Shopify and Amazon',
              'Monitor website uptime and alert on Slack',
            ]).map((example) => (
              <button
                key={example}
                onClick={() => setDescription(example)}
                className="flex items-start gap-2 p-3 text-left text-sm text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all"
              >
                {mode === 'ai' ? <Zap size={14} className="text-indigo-400 flex-shrink-0 mt-0.5" /> : <ArrowRight size={14} className="text-slate-400 flex-shrink-0 mt-0.5" />}
                <span className="line-clamp-2">{example}</span>
              </button>
            ))}
          </div>

          {/* Feature cards */}
          {mode === 'ai' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
              <div className="p-4 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 border border-indigo-100 dark:border-indigo-800 rounded-xl">
                <Bot className="w-8 h-8 text-indigo-500 mb-2" />
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">AI-Powered</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">Claude AI analyzes your description and designs an optimized multi-step workflow</p>
              </div>
              <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-100 dark:border-emerald-800 rounded-xl">
                <Zap className="w-8 h-8 text-emerald-500 mb-2" />
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">Instant Setup</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">Generated workflows are ready to review and publish — no coding required</p>
              </div>
              <div className="p-4 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border border-amber-100 dark:border-amber-800 rounded-xl">
                <Globe className="w-8 h-8 text-amber-500 mb-2" />
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm mb-1">15+ Task Types</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">Web scraping, API calls, data processing, AI analysis, email, files, and more</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
