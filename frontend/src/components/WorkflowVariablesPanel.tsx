/**
 * WorkflowVariablesPanel — Side panel for managing workflow variables.
 *
 * Shows in the workflow editor to define input/output variables, their types,
 * defaults, and descriptions. Also supports step I/O mappings.
 */

import { useState, useEffect } from 'react';
import {
  Variable,
  Plus,
  Trash2,
  X,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Save,
  Loader2,
  Lock,
  Hash,
  ToggleLeft,
  Braces,
  List,
  Type,
} from 'lucide-react';
import type { VarType, VariableDefinition, StepMapping } from '@/api/workflowVariables';
import { workflowVariablesApi } from '@/api/workflowVariables';

const VAR_TYPES: { value: VarType; label: string; icon: React.ElementType; color: string }[] = [
  { value: 'string', label: 'String', icon: Type, color: 'text-blue-500' },
  { value: 'number', label: 'Number', icon: Hash, color: 'text-emerald-500' },
  { value: 'boolean', label: 'Boolean', icon: ToggleLeft, color: 'text-amber-500' },
  { value: 'json', label: 'JSON', icon: Braces, color: 'text-violet-500' },
  { value: 'list', label: 'List', icon: List, color: 'text-indigo-500' },
  { value: 'secret', label: 'Secret', icon: Lock, color: 'text-red-500' },
];

function emptyVar(): VariableDefinition {
  return {
    name: '',
    type: 'string',
    default_value: undefined,
    description: '',
    required: false,
    scope: 'workflow',
    sensitive: false,
  };
}

interface Props {
  workflowId: string;
  onClose: () => void;
}

export default function WorkflowVariablesPanel({ workflowId, onClose }: Props) {
  const [variables, setVariables] = useState<VariableDefinition[]>([]);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const res = await workflowVariablesApi.get(workflowId);
        setVariables(res.variables || []);
      } catch {
        // new workflow — empty is fine
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [workflowId]);

  const addVariable = () => {
    setVariables((prev) => [...prev, emptyVar()]);
    setExpandedIdx(variables.length);
    setDirty(true);
  };

  const removeVariable = (idx: number) => {
    setVariables((prev) => prev.filter((_, i) => i !== idx));
    setExpandedIdx(null);
    setDirty(true);
  };

  const updateVariable = (idx: number, field: keyof VariableDefinition, value: unknown) => {
    setVariables((prev) => prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v)));
    setDirty(true);
  };

  const handleSave = async () => {
    setError('');

    // Validate names
    const names = variables.map((v) => v.name);
    const empty = names.some((n) => !n.trim());
    if (empty) { setError('All variables must have a name'); return; }
    if (new Set(names).size !== names.length) { setError('Variable names must be unique'); return; }
    const invalidName = names.find((n) => !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(n));
    if (invalidName) { setError(`Invalid variable name: "${invalidName}"`); return; }

    setSaving(true);
    try {
      await workflowVariablesApi.update(workflowId, variables);
      setDirty(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const TypeIcon = ({ type }: { type: VarType }) => {
    const t = VAR_TYPES.find((vt) => vt.value === type);
    if (!t) return null;
    const Icon = t.icon;
    return <Icon className={`w-3.5 h-3.5 ${t.color}`} />;
  };

  return (
    <div className="fixed top-0 right-0 h-full w-96 bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 shadow-xl z-40 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Variable className="w-4 h-4 text-indigo-500" />
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Variables</h2>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
            {variables.length}
          </span>
          {dirty && <span className="text-[10px] text-amber-500 font-medium">unsaved</span>}
        </div>
        <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
          </div>
        ) : (
          <>
            {variables.map((v, idx) => (
              <div key={idx} className="bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600">
                {/* Variable header (collapsed) */}
                <button
                  onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                  className="w-full px-3 py-2 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-2">
                    {expandedIdx === idx ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                    <TypeIcon type={v.type} />
                    <span className="text-sm font-mono text-slate-900 dark:text-white">{v.name || 'unnamed'}</span>
                    {v.required && <span className="text-[10px] px-1 py-0 rounded bg-red-50 dark:bg-red-900/30 text-red-500 font-medium">required</span>}
                    {v.sensitive && <Lock className="w-3 h-3 text-red-400" />}
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); removeVariable(idx); }}
                    className="p-1 text-slate-400 hover:text-red-500">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </button>

                {/* Variable details (expanded) */}
                {expandedIdx === idx && (
                  <div className="px-3 pb-3 space-y-2.5 border-t border-slate-200 dark:border-slate-600 pt-2">
                    {/* Name */}
                    <div>
                      <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5 uppercase tracking-wider">Name</label>
                      <input type="text" value={v.name} onChange={(e) => updateVariable(idx, 'name', e.target.value)}
                        placeholder="my_variable"
                        className="w-full px-2.5 py-1.5 text-xs font-mono border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-indigo-500/30 focus:border-indigo-300" />
                    </div>

                    {/* Type */}
                    <div>
                      <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5 uppercase tracking-wider">Type</label>
                      <div className="grid grid-cols-3 gap-1">
                        {VAR_TYPES.map((vt) => (
                          <button key={vt.value} onClick={() => updateVariable(idx, 'type', vt.value)}
                            className={`flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md border transition ${
                              v.type === vt.value
                                ? 'border-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                                : 'border-slate-200 dark:border-slate-600 text-slate-500 hover:border-slate-300'
                            }`}>
                            <vt.icon className={`w-3 h-3 ${vt.color}`} />
                            {vt.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Default value */}
                    <div>
                      <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5 uppercase tracking-wider">Default Value</label>
                      <input type="text" value={v.default_value != null ? String(v.default_value) : ''} onChange={(e) => updateVariable(idx, 'default_value', e.target.value || undefined)}
                        placeholder="optional"
                        className="w-full px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-indigo-500/30 focus:border-indigo-300" />
                    </div>

                    {/* Description */}
                    <div>
                      <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5 uppercase tracking-wider">Description</label>
                      <input type="text" value={v.description} onChange={(e) => updateVariable(idx, 'description', e.target.value)}
                        placeholder="What this variable is for"
                        className="w-full px-2.5 py-1.5 text-xs border border-slate-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-indigo-500/30 focus:border-indigo-300" />
                    </div>

                    {/* Flags */}
                    <div className="flex gap-4">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" checked={v.required} onChange={(e) => updateVariable(idx, 'required', e.target.checked)}
                          className="w-3.5 h-3.5 rounded border-slate-300" />
                        <span className="text-[10px] text-slate-600 dark:text-slate-300">Required</span>
                      </label>
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" checked={v.sensitive} onChange={(e) => updateVariable(idx, 'sensitive', e.target.checked)}
                          className="w-3.5 h-3.5 rounded border-slate-300" />
                        <span className="text-[10px] text-slate-600 dark:text-slate-300">Sensitive</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {variables.length === 0 && (
              <div className="text-center py-8">
                <Variable className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-xs text-slate-400">No variables defined</p>
                <p className="text-[10px] text-slate-400 mt-1">Variables let you pass data between steps</p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700">
        {error && (
          <div className="flex items-center gap-1.5 mb-2 text-[10px] text-red-500">
            <AlertCircle className="w-3 h-3" /> {error}
          </div>
        )}
        <div className="flex items-center justify-between">
          <button onClick={addVariable}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-md transition">
            <Plus className="w-3.5 h-3.5" /> Add Variable
          </button>
          <button onClick={handleSave} disabled={!dirty || saving}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50 transition">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
