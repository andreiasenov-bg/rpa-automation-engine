import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Loader2,
  BookOpen,
  Layers,
  ArrowRight,
  ArrowLeft,
  X,
  Sparkles,
  Clock,
  Tag,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  Brain,
  MessageSquare,
  Zap,
  Check,
} from 'lucide-react';
import {
  templatesApi,
  type TemplateSummary,
  type TemplateParameter,
  type ValidationResult,
  type AIReviewResult,
  type AIFieldAnalysis,
} from '@/api/templates';

/* ━━━ Difficulty badge ━━━ */
const DIFFICULTY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  beginner: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  intermediate: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  advanced: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
};

/* ━━━ Confidence indicator ━━━ */
function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? 'text-emerald-600 bg-emerald-50' :
    pct >= 50 ? 'text-amber-600 bg-amber-50' :
    'text-red-600 bg-red-50';
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${color}`}>
      {pct}%
    </span>
  );
}

/* ━━━ Template Card ━━━ */
function TemplateCard({ template, onUse }: { template: TemplateSummary; onUse: (t: TemplateSummary) => void }) {
  const dc = DIFFICULTY_COLORS[template.difficulty] ?? DIFFICULTY_COLORS.beginner;
  const hasParams = template.required_parameters && template.required_parameters.length > 0;
  const requiredCount = template.required_parameters?.filter(p => p.required).length ?? 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md hover:border-slate-300 transition-all group">
      <div className="flex items-start justify-between mb-3">
        <span className="text-2xl">{template.icon}</span>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${dc.bg} ${dc.text} ${dc.border}`}>
          {template.difficulty}
        </span>
      </div>

      <h3 className="font-semibold text-slate-900 text-sm mb-1 group-hover:text-indigo-600 transition-colors">
        {template.name}
      </h3>
      <p className="text-xs text-slate-500 mb-3 line-clamp-2">{template.description}</p>

      <div className="flex flex-wrap gap-1 mb-3">
        {template.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="text-[10px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
            {tag}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[10px] text-slate-400">
          <span className="flex items-center gap-1">
            <Layers className="w-3 h-3" />
            {template.step_count} step{template.step_count !== 1 ? 's' : ''}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {template.estimated_duration}
          </span>
        </div>

        <button
          onClick={() => onUse(template)}
          className="flex items-center gap-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-700 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {hasParams ? 'Configure' : 'Use'}
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {hasParams && (
        <div className="mt-2 pt-2 border-t border-slate-100">
          <span className="text-[10px] text-slate-400">
            {requiredCount} required field{requiredCount !== 1 ? 's' : ''} to configure
          </span>
        </div>
      )}
    </div>
  );
}

/* ━━━ Parameter Input Field ━━━ */
function ParamField({
  param,
  value,
  onChange,
  fieldStatus,
  aiSuggested,
}: {
  param: TemplateParameter;
  value: string;
  onChange: (key: string, val: string) => void;
  fieldStatus?: { status: string; message: string };
  aiSuggested?: boolean;
}) {
  const isError = fieldStatus?.status === 'error';
  const isOk = fieldStatus?.status === 'ok';
  const borderClass = isError
    ? 'border-red-300 focus:ring-red-500/20 focus:border-red-400'
    : isOk
    ? 'border-emerald-300 focus:ring-emerald-500/20 focus:border-emerald-400'
    : aiSuggested
    ? 'border-violet-300 focus:ring-violet-500/20 focus:border-violet-400'
    : 'border-slate-200 focus:ring-indigo-500/20 focus:border-indigo-300';

  const inputClass = `w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 ${borderClass}`;

  return (
    <div className="mb-4">
      <label className="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
        {param.label}
        {param.required && <span className="text-red-400 text-xs">*</span>}
        {param.type === 'credential' && (
          <span className="ml-1 text-[10px] bg-amber-50 text-amber-600 px-1.5 py-0.5 rounded">credential</span>
        )}
        {aiSuggested && (
          <span className="ml-1 text-[10px] bg-violet-50 text-violet-600 px-1.5 py-0.5 rounded flex items-center gap-0.5">
            <Sparkles className="w-2.5 h-2.5" /> AI
          </span>
        )}
      </label>
      {param.description && (
        <p className="text-xs text-slate-400 mb-1.5">{param.description}</p>
      )}

      {param.type === 'textarea' ? (
        <textarea
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          placeholder={param.placeholder}
          rows={3}
          className={`${inputClass} resize-none`}
        />
      ) : param.type === 'select' && param.options ? (
        <select
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          className={inputClass}
        >
          <option value="">Select...</option>
          {param.options.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      ) : param.type === 'boolean' ? (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={value === 'true'}
            onChange={(e) => onChange(param.key, e.target.checked ? 'true' : 'false')}
            className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-slate-600">{param.placeholder || 'Enable'}</span>
        </label>
      ) : (
        <input
          type={param.type === 'number' ? 'number' : param.type === 'email' ? 'email' : param.type === 'url' ? 'url' : 'text'}
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          placeholder={param.placeholder}
          className={inputClass}
        />
      )}

      {fieldStatus && (
        <div className={`flex items-center gap-1 mt-1 text-xs ${
          isError ? 'text-red-500' : isOk ? 'text-emerald-500' : 'text-amber-500'
        }`}>
          {isError ? <AlertCircle className="w-3 h-3" /> : isOk ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
          {fieldStatus.message}
        </div>
      )}
    </div>
  );
}

/* ━━━ AI Suggestion Card ━━━ */
function AISuggestionCard({
  analysis,
  paramLabel,
  onApply,
  applied,
}: {
  analysis: AIFieldAnalysis;
  paramLabel: string;
  onApply: () => void;
  applied: boolean;
}) {
  return (
    <div className={`p-3 rounded-lg border transition-all ${
      applied ? 'bg-violet-50/50 border-violet-200' : 'bg-white border-slate-200 hover:border-violet-200'
    }`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-slate-700">{paramLabel}</span>
        <div className="flex items-center gap-2">
          <ConfidenceBadge value={analysis.confidence} />
          {analysis.suggested_value && !applied && (
            <button
              onClick={onApply}
              className="text-[10px] font-medium text-violet-600 bg-violet-50 hover:bg-violet-100 px-2 py-0.5 rounded transition-colors"
            >
              Apply
            </button>
          )}
          {applied && (
            <span className="flex items-center gap-0.5 text-[10px] text-emerald-600">
              <Check className="w-3 h-3" /> Applied
            </span>
          )}
        </div>
      </div>
      {analysis.suggested_value && (
        <p className="text-xs font-mono text-violet-700 bg-violet-50 px-2 py-1 rounded mb-1 break-all">
          {analysis.suggested_value}
        </p>
      )}
      <p className="text-xs text-slate-500">{analysis.reason}</p>
    </div>
  );
}

/* ━━━ WIZARD STEP NAMES ━━━ */
const STEP_NAMES = ['Describe', 'AI Review', 'Configure', 'Validate', 'Create'];

/* ━━━ Create Wizard Modal ━━━ */
function CreateWizardModal({
  template,
  onClose,
  onCreated,
}: {
  template: TemplateSummary;
  onClose: () => void;
  onCreated: (workflowId: string) => void;
}) {
  const params = template.required_parameters ?? [];
  const hasParams = params.length > 0;

  // 5-step wizard: 0=Describe, 1=AI Review, 2=Configure, 3=Validate, 4=Create
  const [step, setStep] = useState(hasParams ? 0 : 4);
  const [instruction, setInstruction] = useState('');
  const [paramValues, setParamValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {};
    params.forEach(p => {
      if (p.default !== undefined) defaults[p.key] = String(p.default);
    });
    return defaults;
  });
  const [aiReview, setAiReview] = useState<AIReviewResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<string>>(new Set());
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);
  const [name, setName] = useState(template.name);
  const [desc, setDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const handleParamChange = useCallback((key: string, val: string) => {
    setParamValues(prev => ({ ...prev, [key]: val }));
    setValidation(null);
  }, []);

  const handleAIReview = async () => {
    setAiLoading(true);
    setError('');
    try {
      const result = await templatesApi.aiReview(template.id, instruction, paramValues);
      setAiReview(result);
      setStep(1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'AI review failed';
      setError(msg);
    } finally {
      setAiLoading(false);
    }
  };

  const handleApplySuggestion = (key: string, value: string) => {
    setParamValues(prev => ({ ...prev, [key]: value }));
    setAppliedSuggestions(prev => new Set([...prev, key]));
  };

  const handleApplyAll = () => {
    if (!aiReview) return;
    const newValues = { ...paramValues };
    const newApplied = new Set(appliedSuggestions);
    for (const [key, value] of Object.entries(aiReview.suggested_parameters)) {
      if (value && params.find(p => p.key === key && p.type !== 'credential')) {
        newValues[key] = value;
        newApplied.add(key);
      }
    }
    setParamValues(newValues);
    setAppliedSuggestions(newApplied);
  };

  const handleValidate = async () => {
    setValidating(true);
    setError('');
    try {
      const result = await templatesApi.validate(template.id, paramValues);
      setValidation(result);
      if (result.valid) {
        setTimeout(() => setStep(4), 600);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Validation failed';
      setError(msg);
    } finally {
      setValidating(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const result = await templatesApi.instantiate({
        templateId: template.id,
        name,
        description: desc || undefined,
        parameters: hasParams ? paramValues : undefined,
        instruction: instruction || undefined,
      });
      onCreated(result.workflow_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create workflow';
      setError(msg);
    } finally {
      setCreating(false);
    }
  };

  const requiredParams = params.filter(p => p.required);
  const optionalParams = params.filter(p => !p.required);
  const allRequiredFilled = requiredParams.every(p => paramValues[p.key]?.trim());

  // Get label for a param key
  const getParamLabel = (key: string) => params.find(p => p.key === key)?.label ?? key;

  // Determine which step subtitle to show
  const stepSubtitle = hasParams
    ? `Step ${step + 1} — ${STEP_NAMES[step]}`
    : 'Create workflow from template';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{template.icon}</span>
            <div>
              <h2 className="text-base font-semibold text-slate-900">{template.name}</h2>
              <p className="text-xs text-slate-400">{stepSubtitle}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors">
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* Progress bar */}
        {hasParams && (
          <div className="flex gap-1 px-6 pt-3">
            {[0, 1, 2, 3, 4].map(s => (
              <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${
                s <= step ? 'bg-indigo-500' : 'bg-slate-100'
              }`} />
            ))}
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* ━━━ Step 0: Describe — What should this workflow do? ━━━ */}
          {step === 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare className="w-5 h-5 text-indigo-500" />
                <h3 className="text-sm font-semibold text-slate-700">
                  What should this workflow do?
                </h3>
              </div>

              <div className="mb-4">
                <label className="text-sm font-medium text-slate-700 mb-1 block">
                  Instructions <span className="text-red-400 text-xs">*</span>
                </label>
                <p className="text-xs text-slate-400 mb-2">
                  Describe in detail what you want this workflow to accomplish. AI will analyze your description and suggest optimal configuration.
                </p>
                <textarea
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder={`Example: "Scrape laptop prices from emag.bg every day and alert me when prices drop below 1500 lv"`}
                  rows={4}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 resize-none"
                />
              </div>

              <div className="mb-4">
                <label className="text-sm font-medium text-slate-700 mb-1 block">
                  Workflow Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={template.name}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
                />
              </div>

              <div className="p-3 bg-violet-50 rounded-lg border border-violet-100">
                <div className="flex items-center gap-2 mb-1">
                  <Brain className="w-4 h-4 text-violet-500" />
                  <span className="text-xs font-medium text-violet-700">AI-Assisted Configuration</span>
                </div>
                <p className="text-xs text-violet-600">
                  After you describe your task, AI will review the template architecture, suggest parameter values,
                  and auto-fill fields it can determine from public information.
                </p>
              </div>
            </div>
          )}

          {/* ━━━ Step 1: AI Review — Suggestions ━━━ */}
          {step === 1 && (
            <div>
              {aiLoading ? (
                <div className="flex flex-col items-center py-8 gap-3">
                  <div className="relative">
                    <Brain className="w-10 h-10 text-violet-500" />
                    <Loader2 className="w-5 h-5 text-violet-400 animate-spin absolute -bottom-1 -right-1" />
                  </div>
                  <p className="text-sm text-slate-500">AI is analyzing your instruction...</p>
                  <p className="text-xs text-slate-400">Reviewing template architecture and suggesting parameters</p>
                </div>
              ) : aiReview ? (
                <div className="space-y-4">
                  {/* Overall analysis */}
                  <div className={`p-4 rounded-xl border ${
                    aiReview.overall_confidence >= 0.7
                      ? 'bg-violet-50 border-violet-200'
                      : aiReview.overall_confidence >= 0.4
                      ? 'bg-amber-50 border-amber-200'
                      : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="flex items-center gap-2 mb-2">
                      <Brain className="w-5 h-5 text-violet-500" />
                      <span className="text-sm font-medium text-slate-700">AI Analysis</span>
                      <ConfidenceBadge value={aiReview.overall_confidence} />
                    </div>
                    <p className="text-sm text-slate-600">{aiReview.explanation}</p>
                  </div>

                  {/* Suggestions */}
                  {aiReview.field_analysis.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Parameter Suggestions
                        </h4>
                        {Object.keys(aiReview.suggested_parameters).length > 0 && (
                          <button
                            onClick={handleApplyAll}
                            className="flex items-center gap-1 text-[11px] font-medium text-violet-600 hover:text-violet-700 bg-violet-50 hover:bg-violet-100 px-2.5 py-1 rounded-md transition-colors"
                          >
                            <Zap className="w-3 h-3" />
                            Apply All
                          </button>
                        )}
                      </div>
                      <div className="space-y-2">
                        {aiReview.field_analysis.map(fa => (
                          <AISuggestionCard
                            key={fa.key}
                            analysis={fa}
                            paramLabel={getParamLabel(fa.key)}
                            onApply={() => fa.suggested_value && handleApplySuggestion(fa.key, fa.suggested_value)}
                            applied={appliedSuggestions.has(fa.key)}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Warnings */}
                  {aiReview.warnings.length > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-xs font-medium text-amber-700 mb-1 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> Warnings
                      </p>
                      {aiReview.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-amber-600 mt-0.5">{w}</p>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* ━━━ Step 2: Configure Parameters ━━━ */}
          {step === 2 && (
            <div>
              {instruction && (
                <div className="mb-4 p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <p className="text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                    <MessageSquare className="w-3 h-3" /> Your instruction:
                  </p>
                  <p className="text-xs text-slate-600 italic">{instruction}</p>
                </div>
              )}

              {requiredParams.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    Required Fields
                  </h3>
                  {requiredParams.map(p => (
                    <ParamField
                      key={p.key}
                      param={p}
                      value={paramValues[p.key] ?? ''}
                      onChange={handleParamChange}
                      fieldStatus={validation?.fields[p.key]}
                      aiSuggested={appliedSuggestions.has(p.key)}
                    />
                  ))}
                </div>
              )}

              {optionalParams.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                    Optional Fields
                  </h3>
                  {optionalParams.map(p => (
                    <ParamField
                      key={p.key}
                      param={p}
                      value={paramValues[p.key] ?? ''}
                      onChange={handleParamChange}
                      fieldStatus={validation?.fields[p.key]}
                      aiSuggested={appliedSuggestions.has(p.key)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ━━━ Step 3: Validation Results ━━━ */}
          {step === 3 && (
            <div>
              {validating ? (
                <div className="flex flex-col items-center py-8 gap-3">
                  <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                  <p className="text-sm text-slate-500">Validating parameters...</p>
                </div>
              ) : validation ? (
                <div className="space-y-3">
                  <div className={`p-4 rounded-xl border flex items-center gap-3 ${
                    validation.valid
                      ? 'bg-emerald-50 border-emerald-200'
                      : 'bg-red-50 border-red-200'
                  }`}>
                    {validation.valid
                      ? <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                      : <AlertCircle className="w-6 h-6 text-red-500" />
                    }
                    <div>
                      <p className={`text-sm font-medium ${validation.valid ? 'text-emerald-700' : 'text-red-700'}`}>
                        {validation.valid ? 'All parameters are valid!' : 'Some parameters need attention'}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {validation.valid
                          ? 'Your workflow is ready to be created.'
                          : `${validation.errors.length} error${validation.errors.length !== 1 ? 's' : ''} found`
                        }
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {params.map(p => {
                      const fs = validation.fields[p.key];
                      if (!fs) return null;
                      return (
                        <div key={p.key} className={`flex items-center gap-2 p-2.5 rounded-lg text-sm ${
                          fs.status === 'ok' ? 'bg-emerald-50/50' : fs.status === 'error' ? 'bg-red-50/50' : 'bg-amber-50/50'
                        }`}>
                          {fs.status === 'ok'
                            ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                            : fs.status === 'error'
                            ? <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
                            : <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                          }
                          <span className="font-medium text-slate-700">{p.label}</span>
                          <span className="text-slate-400 ml-auto text-xs">{fs.message}</span>
                        </div>
                      );
                    })}
                  </div>

                  {validation.warnings.length > 0 && (
                    <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-xs font-medium text-amber-700 mb-1">Warnings:</p>
                      {validation.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-amber-600">{w.message}</p>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* ━━━ Step 4: Name & Create ━━━ */}
          {step === 4 && (
            <div>
              {hasParams && validation?.valid && (
                <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span className="text-sm text-emerald-700">Parameters validated successfully</span>
                </div>
              )}

              {instruction && (
                <div className="mb-4 p-3 bg-violet-50 rounded-lg border border-violet-100">
                  <p className="text-xs font-medium text-violet-600 mb-1 flex items-center gap-1">
                    <Brain className="w-3 h-3" /> Instruction:
                  </p>
                  <p className="text-xs text-violet-700 italic">{instruction}</p>
                </div>
              )}

              <div className="mb-4">
                <label className="text-sm font-medium text-slate-700 mb-1 block">
                  Workflow Name <span className="text-red-400 text-xs">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700 mb-1 block">
                  Description
                </label>
                <textarea
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  rows={3}
                  placeholder="Optional description for this workflow..."
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 resize-none"
                />
              </div>

              {hasParams && (
                <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs font-medium text-slate-500 mb-2">Configured Parameters:</p>
                  <div className="space-y-1">
                    {params.filter(p => paramValues[p.key]?.trim()).map(p => (
                      <div key={p.key} className="flex items-center justify-between text-xs">
                        <span className="text-slate-500 flex items-center gap-1">
                          {p.label}
                          {appliedSuggestions.has(p.key) && (
                            <Sparkles className="w-2.5 h-2.5 text-violet-400" />
                          )}
                        </span>
                        <span className="text-slate-700 font-mono truncate ml-2 max-w-[200px]">
                          {p.type === 'credential' ? '••••••' : paramValues[p.key]}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100">
          <div>
            {step > 0 && hasParams && (
              <button
                onClick={() => {
                  if (step === 3 && !validation?.valid) {
                    setStep(2);
                  } else {
                    setStep(step - 1);
                  }
                  setError('');
                }}
                className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 hover:text-slate-900 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
            >
              Cancel
            </button>

            {/* Step 0: Describe → trigger AI review */}
            {step === 0 && (
              <button
                onClick={() => { handleAIReview(); setStep(1); }}
                disabled={!instruction.trim() || aiLoading}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {aiLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="w-3.5 h-3.5" />
                    Review with AI
                  </>
                )}
              </button>
            )}

            {/* Step 1: AI Review → go to Configure */}
            {step === 1 && !aiLoading && aiReview && (
              <button
                onClick={() => setStep(2)}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
              >
                Configure
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Step 2: Configure → Validate */}
            {step === 2 && (
              <button
                onClick={() => { setStep(3); handleValidate(); }}
                disabled={!allRequiredFilled}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Validate
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Step 3: Validation failed → Fix */}
            {step === 3 && validation && !validation.valid && (
              <button
                onClick={() => { setStep(2); setValidation(null); }}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-lg transition-colors"
              >
                Fix Errors
              </button>
            )}

            {/* Step 4: Create */}
            {step === 4 && (
              <button
                onClick={handleCreate}
                disabled={!name.trim() || creating}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {creating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    Create Workflow
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ━━━ Main Templates Page ━━━ */
export default function TemplatesPage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('');
  const [wizardTemplate, setWizardTemplate] = useState<TemplateSummary | null>(null);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const [tplRes, catRes] = await Promise.all([
        templatesApi.list({
          category: selectedCategory || undefined,
          difficulty: selectedDifficulty || undefined,
          search: search || undefined,
        }),
        templatesApi.categories(),
      ]);
      setTemplates(tplRes.templates);
      setCategories(catRes);
    } catch {
      // handle error
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedDifficulty, search]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleUse = (template: TemplateSummary) => {
    setWizardTemplate(template);
  };

  const handleCreated = (workflowId: string) => {
    setWizardTemplate(null);
    navigate(`/workflows/${workflowId}/edit`);
  };

  const difficulties = ['beginner', 'intermediate', 'advanced'];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-indigo-500" />
            Workflow Templates
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Pre-built automation workflows ready to configure and deploy
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search templates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 bg-white"
          />
        </div>

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 bg-white"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <div className="flex gap-1">
          {difficulties.map((d) => {
            const dc = DIFFICULTY_COLORS[d];
            const active = selectedDifficulty === d;
            return (
              <button
                key={d}
                onClick={() => setSelectedDifficulty(active ? '' : d)}
                className={`px-2.5 py-1.5 text-[11px] font-medium rounded-md border transition-all ${
                  active
                    ? `${dc.bg} ${dc.text} ${dc.border}`
                    : 'bg-white text-slate-400 border-slate-200 hover:border-slate-300'
                }`}
              >
                {d}
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-16">
          <Info className="w-8 h-8 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No templates found matching your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {templates.map((t) => (
            <TemplateCard key={t.id} template={t} onUse={handleUse} />
          ))}
        </div>
      )}

      {/* Wizard Modal */}
      {wizardTemplate && (
        <CreateWizardModal
          template={wizardTemplate}
          onClose={() => setWizardTemplate(null)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
