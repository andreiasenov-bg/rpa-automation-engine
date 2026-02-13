/**
 * StepConfigEditor — Side panel for editing a workflow step's configuration.
 *
 * Shows when a node is clicked in the workflow editor. Allows editing:
 * - Step name, type, on_error behavior
 * - Type-specific config fields (URL, selectors, headers, etc.)
 * - Retry strategy per step
 */

import { useState, useEffect } from 'react';
import {
  X,
  Save,
  Settings2,
  Loader2,
  Plus,
  Trash2,
  AlertCircle,
  Globe2,
  Search,
  FileText,
  Mail,
  Database,
  Code2,
  Clock,
  GitFork,
  Repeat,
  FolderOpen,
} from 'lucide-react';

interface StepData {
  id: string;
  label: string;
  type: string;
  config: Record<string, unknown>;
  color: string;
}

interface Props {
  step: StepData;
  allStepIds: string[];
  onSave: (stepId: string, updates: { label: string; config: Record<string, unknown>; on_error?: string }) => void;
  onClose: () => void;
}

/* ─── Type-specific config field definitions ─── */
const TYPE_FIELDS: Record<string, Array<{ key: string; label: string; type: 'text' | 'textarea' | 'number' | 'boolean' | 'select'; placeholder?: string; options?: string[] }>> = {
  web_scraping: [
    { key: 'url', label: 'URL', type: 'text', placeholder: 'https://example.com' },
    { key: 'selector', label: 'CSS Selector', type: 'text', placeholder: 'div.content > p' },
    { key: 'wait_for', label: 'Wait For Selector', type: 'text', placeholder: '.loaded' },
    { key: 'timeout_ms', label: 'Timeout (ms)', type: 'number', placeholder: '30000' },
    { key: 'use_js', label: 'Execute JavaScript', type: 'boolean' },
    { key: 'extract_text', label: 'Extract Text Only', type: 'boolean' },
  ],
  api_request: [
    { key: 'url', label: 'URL', type: 'text', placeholder: 'https://api.example.com/data' },
    { key: 'method', label: 'Method', type: 'select', options: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] },
    { key: 'headers', label: 'Headers (JSON)', type: 'textarea', placeholder: '{"Authorization": "Bearer ..."}' },
    { key: 'body', label: 'Body (JSON)', type: 'textarea', placeholder: '{"key": "value"}' },
    { key: 'timeout_ms', label: 'Timeout (ms)', type: 'number', placeholder: '30000' },
    { key: 'expected_status', label: 'Expected Status', type: 'number', placeholder: '200' },
  ],
  form_filling: [
    { key: 'url', label: 'Form URL', type: 'text', placeholder: 'https://example.com/form' },
    { key: 'fields', label: 'Fields (JSON)', type: 'textarea', placeholder: '[{"selector": "#name", "value": "John"}]' },
    { key: 'submit_selector', label: 'Submit Button', type: 'text', placeholder: 'button[type=submit]' },
    { key: 'screenshot_after', label: 'Screenshot After Submit', type: 'boolean' },
  ],
  email: [
    { key: 'to', label: 'To', type: 'text', placeholder: 'user@example.com' },
    { key: 'subject', label: 'Subject', type: 'text', placeholder: 'Report ready' },
    { key: 'body_template', label: 'Body Template', type: 'textarea', placeholder: 'Hello {{name}},\n\nYour report is ready.' },
    { key: 'use_html', label: 'HTML Email', type: 'boolean' },
  ],
  database: [
    { key: 'connection_string', label: 'Connection String', type: 'text', placeholder: 'postgresql://user:pass@host/db' },
    { key: 'query', label: 'SQL Query', type: 'textarea', placeholder: 'SELECT * FROM users WHERE active = true' },
    { key: 'credential_id', label: 'Credential ID', type: 'text', placeholder: 'Use vault credential' },
  ],
  file_ops: [
    { key: 'operation', label: 'Operation', type: 'select', options: ['read', 'write', 'copy', 'move', 'delete', 'list'] },
    { key: 'source_path', label: 'Source Path', type: 'text', placeholder: '/data/input.csv' },
    { key: 'destination_path', label: 'Destination Path', type: 'text', placeholder: '/data/output.csv' },
    { key: 'content', label: 'Content (for write)', type: 'textarea', placeholder: 'File content...' },
  ],
  custom_script: [
    { key: 'language', label: 'Language', type: 'select', options: ['python', 'javascript', 'bash'] },
    { key: 'code', label: 'Script', type: 'textarea', placeholder: '# Your code here\nresult = "hello"' },
    { key: 'timeout_ms', label: 'Timeout (ms)', type: 'number', placeholder: '60000' },
  ],
  conditional: [
    { key: 'condition', label: 'Condition Expression', type: 'text', placeholder: '{{result.status}} == "success"' },
    { key: 'true_branch', label: 'True Branch Step ID', type: 'text' },
    { key: 'false_branch', label: 'False Branch Step ID', type: 'text' },
  ],
  loop: [
    { key: 'loop_type', label: 'Loop Type', type: 'select', options: ['for_each', 'while', 'count'] },
    { key: 'items_expression', label: 'Items / Condition', type: 'text', placeholder: '{{data.items}}' },
    { key: 'max_iterations', label: 'Max Iterations', type: 'number', placeholder: '100' },
    { key: 'body_step_id', label: 'Body Step ID', type: 'text' },
  ],
  delay: [
    { key: 'duration_ms', label: 'Duration (ms)', type: 'number', placeholder: '5000' },
    { key: 'until', label: 'Until (ISO datetime)', type: 'text', placeholder: '2026-01-01T00:00:00Z' },
  ],
};

const RETRY_POLICIES = ['none', 'fixed', 'exponential', 'linear'];

export default function StepConfigEditor({ step, allStepIds, onSave, onClose }: Props) {
  const [label, setLabel] = useState(step.label);
  const [config, setConfig] = useState<Record<string, unknown>>({ ...step.config });
  const [onError, setOnError] = useState<string>((step.config._on_error as string) || '');
  const [retryPolicy, setRetryPolicy] = useState<string>((step.config._retry_policy as string) || 'none');
  const [retryMaxAttempts, setRetryMaxAttempts] = useState<number>((step.config._retry_max_attempts as number) || 3);

  const fields = TYPE_FIELDS[step.type] || [];

  const updateConfig = (key: string, value: unknown) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    const finalConfig = { ...config };
    if (retryPolicy !== 'none') {
      finalConfig._retry_policy = retryPolicy;
      finalConfig._retry_max_attempts = retryMaxAttempts;
    }
    onSave(step.id, { label, config: finalConfig, on_error: onError || undefined });
    onClose();
  };

  return (
    <div className="fixed top-0 right-0 h-full w-[420px] bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 shadow-xl z-40 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-indigo-500" />
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Step Config</h2>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 font-mono">{step.type}</span>
        </div>
        <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Step name */}
        <div>
          <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wider">Step Name</label>
          <input type="text" value={label} onChange={(e) => setLabel(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
        </div>

        {/* Type-specific fields */}
        {fields.length > 0 && (
          <div>
            <p className="text-[10px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Configuration</p>
            <div className="space-y-3">
              {fields.map((field) => (
                <div key={field.key}>
                  <label className="block text-xs text-slate-600 dark:text-slate-300 mb-1">{field.label}</label>
                  {field.type === 'text' && (
                    <input type="text" value={(config[field.key] as string) || ''} onChange={(e) => updateConfig(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      className="w-full px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-indigo-500/30 focus:border-indigo-300" />
                  )}
                  {field.type === 'textarea' && (
                    <textarea value={(config[field.key] as string) || ''} onChange={(e) => updateConfig(field.key, e.target.value)}
                      placeholder={field.placeholder} rows={3}
                      className="w-full px-2.5 py-1.5 text-xs font-mono border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-indigo-500/30 focus:border-indigo-300 resize-none" />
                  )}
                  {field.type === 'number' && (
                    <input type="number" value={(config[field.key] as number) || ''} onChange={(e) => updateConfig(field.key, e.target.value ? Number(e.target.value) : undefined)}
                      placeholder={field.placeholder}
                      className="w-full px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-indigo-500/30 focus:border-indigo-300" />
                  )}
                  {field.type === 'boolean' && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={!!config[field.key]} onChange={(e) => updateConfig(field.key, e.target.checked)}
                        className="w-3.5 h-3.5 rounded border-slate-300" />
                      <span className="text-xs text-slate-500">{field.label}</span>
                    </label>
                  )}
                  {field.type === 'select' && (
                    <select value={(config[field.key] as string) || ''} onChange={(e) => updateConfig(field.key, e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white">
                      <option value="">Select...</option>
                      {field.options?.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error handling */}
        <div>
          <p className="text-[10px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Error Handling</p>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-600 dark:text-slate-300 mb-1">On Error → Go To Step</label>
              <select value={onError} onChange={(e) => setOnError(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white">
                <option value="">Fail execution</option>
                {allStepIds.filter((sid) => sid !== step.id).map((sid) => (
                  <option key={sid} value={sid}>{sid}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 dark:text-slate-300 mb-1">Retry Policy</label>
              <div className="grid grid-cols-4 gap-1">
                {RETRY_POLICIES.map((p) => (
                  <button key={p} onClick={() => setRetryPolicy(p)}
                    className={`px-2 py-1 text-[10px] font-medium rounded-md border transition capitalize ${
                      retryPolicy === p ? 'border-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600' : 'border-slate-200 dark:border-slate-600 text-slate-500 hover:border-slate-300'
                    }`}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
            {retryPolicy !== 'none' && (
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-300 mb-1">Max Attempts</label>
                <input type="number" value={retryMaxAttempts} onChange={(e) => setRetryMaxAttempts(Number(e.target.value) || 3)}
                  min={1} max={10}
                  className="w-24 px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white" />
              </div>
            )}
          </div>
        </div>

        {/* Step ID (read-only) */}
        <div>
          <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wider">Step ID</label>
          <p className="text-xs font-mono text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-700/50 px-2.5 py-1.5 rounded-md">{step.id}</p>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex justify-end">
        <button onClick={handleSave}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition">
          <Save className="w-3.5 h-3.5" /> Save Config
        </button>
      </div>
    </div>
  );
}
