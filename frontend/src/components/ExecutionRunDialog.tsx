/**
 * ExecutionRunDialog — Modal for passing variables when starting a workflow execution.
 *
 * Fetches the workflow's variable schema and presents input fields for each
 * required/optional variable. Validates before submitting.
 */

import { useState, useEffect } from 'react';
import {
  X,
  Play,
  Loader2,
  AlertCircle,
  Variable,
  Hash,
  ToggleLeft,
  Braces,
  List,
  Lock,
  Type,
} from 'lucide-react';
import { workflowVariablesApi, type VariableDefinition, type VarType } from '@/api/workflowVariables';
import { workflowApi } from '@/api/workflows';

const TYPE_ICONS: Record<VarType, React.ElementType> = {
  string: Type,
  number: Hash,
  boolean: ToggleLeft,
  json: Braces,
  list: List,
  secret: Lock,
};

interface Props {
  workflowId: string;
  workflowName: string;
  onClose: () => void;
  onStarted: (executionId: string) => void;
}

export default function ExecutionRunDialog({ workflowId, workflowName, onClose, onStarted }: Props) {
  const [variables, setVariables] = useState<VariableDefinition[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [errors, setErrors] = useState<Array<{ variable: string; error: string }>>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await workflowVariablesApi.get(workflowId);
        setVariables(res.variables || []);
        // Pre-fill defaults
        const defaults: Record<string, unknown> = {};
        for (const v of (res.variables || [])) {
          if (v.default_value !== undefined && v.default_value !== null) {
            defaults[v.name] = v.default_value;
          }
        }
        setValues(defaults);
      } catch {
        // No variables defined — run without
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [workflowId]);

  const setValue = (name: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => prev.filter((e) => e.variable !== name));
  };

  const handleRun = async () => {
    setErrors([]);
    setRunning(true);

    try {
      // Validate if variables exist
      if (variables.length > 0) {
        const validation = await workflowVariablesApi.validate(workflowId, values);
        if (!validation.valid) {
          setErrors(validation.errors);
          setRunning(false);
          return;
        }
      }

      // Execute
      const result = await workflowApi.execute(workflowId, values);
      onStarted(result?.id || '');
    } catch (e: any) {
      setErrors([{ variable: '_general', error: e?.response?.data?.detail || 'Failed to start execution' }]);
    } finally {
      setRunning(false);
    }
  };

  const getFieldError = (name: string) => errors.find((e) => e.variable === name)?.error;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Play className="w-5 h-5 text-indigo-500" /> Run Workflow
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">{workflowName}</p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
            </div>
          ) : variables.length === 0 ? (
            <div className="text-center py-8">
              <Play className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No input variables defined.</p>
              <p className="text-xs text-slate-400 mt-1">The workflow will run with default settings.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {variables.filter((v) => v.required).length} required, {variables.filter((v) => !v.required).length} optional variable{variables.length !== 1 ? 's' : ''}
              </p>

              {variables.map((v) => {
                const Icon = TYPE_ICONS[v.type] || Type;
                const err = getFieldError(v.name);

                return (
                  <div key={v.name}>
                    <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">
                      <Icon className="w-3 h-3 text-slate-400" />
                      {v.name}
                      {v.required && <span className="text-red-500">*</span>}
                      <span className="text-[10px] text-slate-400 font-normal ml-1">({v.type})</span>
                    </label>
                    {v.description && <p className="text-[10px] text-slate-400 mb-1">{v.description}</p>}

                    {v.type === 'boolean' ? (
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={!!values[v.name]} onChange={(e) => setValue(v.name, e.target.checked)}
                          className="w-4 h-4 rounded border-slate-300" />
                        <span className="text-xs text-slate-500">{values[v.name] ? 'true' : 'false'}</span>
                      </label>
                    ) : v.type === 'json' || v.type === 'list' ? (
                      <textarea
                        value={typeof values[v.name] === 'string' ? (values[v.name] as string) : JSON.stringify(values[v.name] || '', null, 2)}
                        onChange={(e) => {
                          try { setValue(v.name, JSON.parse(e.target.value)); }
                          catch { setValue(v.name, e.target.value); }
                        }}
                        rows={3}
                        placeholder={v.type === 'list' ? '["item1", "item2"]' : '{"key": "value"}'}
                        className={`w-full px-3 py-2 text-xs font-mono border rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white resize-none focus:ring-2 focus:ring-indigo-500/20 ${err ? 'border-red-300' : 'border-slate-200 dark:border-slate-600'}`}
                      />
                    ) : (
                      <input
                        type={v.type === 'number' ? 'number' : v.sensitive ? 'password' : 'text'}
                        value={values[v.name] != null ? String(values[v.name]) : ''}
                        onChange={(e) => setValue(v.name, v.type === 'number' ? (e.target.value ? Number(e.target.value) : undefined) : e.target.value)}
                        placeholder={v.default_value != null ? `Default: ${v.default_value}` : undefined}
                        className={`w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 ${err ? 'border-red-300' : 'border-slate-200 dark:border-slate-600'}`}
                      />
                    )}

                    {err && (
                      <p className="flex items-center gap-1 text-[10px] text-red-500 mt-0.5">
                        <AlertCircle className="w-3 h-3" /> {err}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* General error */}
          {errors.find((e) => e.variable === '_general') && (
            <div className="mt-4 flex items-center gap-2 text-xs text-red-500 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {errors.find((e) => e.variable === '_general')?.error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2 flex-shrink-0">
          <button onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition">
            Cancel
          </button>
          <button onClick={handleRun} disabled={running}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Run
          </button>
        </div>
      </div>
    </div>
  );
}
