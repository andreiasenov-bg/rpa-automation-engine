import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  Handle,
  Position,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Save,
  ArrowLeft,
  Play,
  Globe,
  Plus,
  Loader2,
  Trash2,
  Globe2,
  FileText,
  Mail,
  Database,
  Code2,
  Clock,
  GitFork,
  Repeat,
  FolderOpen,
  Search,
} from 'lucide-react';
import { workflowApi } from '@/api/workflows';
import type { Workflow, WorkflowStep } from '@/types';

/* ─── Task palette ─── */
const TASK_TYPES = [
  { type: 'web_scraping', label: 'Web Scraping', icon: Search, color: '#6366f1' },
  { type: 'api_request', label: 'API Request', icon: Globe2, color: '#0ea5e9' },
  { type: 'form_filling', label: 'Form Fill', icon: FileText, color: '#8b5cf6' },
  { type: 'email', label: 'Email', icon: Mail, color: '#f59e0b' },
  { type: 'database', label: 'Database', icon: Database, color: '#10b981' },
  { type: 'file_ops', label: 'File Ops', icon: FolderOpen, color: '#ec4899' },
  { type: 'custom_script', label: 'Script', icon: Code2, color: '#64748b' },
  { type: 'conditional', label: 'Condition', icon: GitFork, color: '#f97316' },
  { type: 'loop', label: 'Loop', icon: Repeat, color: '#14b8a6' },
  { type: 'delay', label: 'Delay', icon: Clock, color: '#94a3b8' },
];

/* ─── Custom node component ─── */
function StepNode({ data }: { data: { label: string; type: string; color: string } }) {
  const taskDef = TASK_TYPES.find((t) => t.type === data.type);
  const Icon = taskDef?.icon || Code2;
  const color = data.color || taskDef?.color || '#6366f1';

  return (
    <div className="bg-white rounded-xl border-2 shadow-sm min-w-[160px]" style={{ borderColor: color }}>
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white" />
      <div className="px-3 py-2.5 flex items-center gap-2.5">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${color}15`, color }}
        >
          <Icon className="w-3.5 h-3.5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-slate-700 truncate">{data.label}</p>
          <p className="text-[10px] text-slate-400 capitalize">{data.type.replace(/_/g, ' ')}</p>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white" />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  stepNode: StepNode,
};

/* ─── Convert backend steps ↔ React Flow ─── */
function stepsToNodesEdges(steps: WorkflowStep[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = steps.map((step, idx) => ({
    id: step.id,
    type: 'stepNode',
    position: step.position || { x: 250, y: idx * 120 },
    data: {
      label: step.name || step.type,
      type: step.type,
      config: step.config,
      color: TASK_TYPES.find((t) => t.type === step.type)?.color || '#6366f1',
    },
  }));

  const edges: Edge[] = [];
  steps.forEach((step) => {
    if (step.next) {
      step.next.forEach((targetId) => {
        edges.push({
          id: `${step.id}-${targetId}`,
          source: step.id,
          target: targetId,
          animated: true,
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        });
      });
    }
  });

  return { nodes, edges };
}

function nodesEdgesToSteps(nodes: Node[], edges: Edge[]): WorkflowStep[] {
  return nodes.map((node) => {
    const outgoing = edges.filter((e) => e.source === node.id).map((e) => e.target);
    return {
      id: node.id,
      type: node.data.type as string,
      name: node.data.label as string,
      config: (node.data.config as Record<string, unknown>) || {},
      next: outgoing.length > 0 ? outgoing : undefined,
      position: node.position,
    };
  });
}

/* ─── Editor page ─── */
export default function WorkflowEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [showPalette, setShowPalette] = useState(false);
  const counterRef = useRef(0);

  // Fetch workflow
  useEffect(() => {
    if (!id) return;
    const load = async () => {
      try {
        const wf = await workflowApi.get(id);
        setWorkflow(wf);
        setName(wf.name);
        setDescription(wf.description || '');
        const { nodes: n, edges: e } = stepsToNodesEdges(wf.definition?.steps || []);
        setNodes(n);
        setEdges(e);
        counterRef.current = n.length;
      } catch {
        navigate('/workflows');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  // Track changes
  useEffect(() => {
    if (workflow) setDirty(true);
  }, [nodes, edges, name, description]);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#94a3b8', strokeWidth: 2 } }, eds));
    },
    [setEdges],
  );

  const addNode = (taskType: string) => {
    counterRef.current += 1;
    const taskDef = TASK_TYPES.find((t) => t.type === taskType)!;
    const newNode: Node = {
      id: `step_${Date.now()}_${counterRef.current}`,
      type: 'stepNode',
      position: { x: 250, y: nodes.length * 120 + 50 },
      data: {
        label: `${taskDef.label} ${counterRef.current}`,
        type: taskType,
        config: {},
        color: taskDef.color,
      },
    };
    setNodes((nds) => [...nds, newNode]);
    setShowPalette(false);
  };

  const handleSave = async () => {
    if (!id || !workflow) return;
    setSaving(true);
    try {
      const steps = nodesEdgesToSteps(nodes, edges);
      const updated = await workflowApi.update(id, {
        name,
        description,
        definition: { steps, variables: workflow.definition?.variables || {} },
      });
      setWorkflow(updated);
      setDirty(false);
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!id) return;
    await handleSave();
    try {
      const updated = await workflowApi.publish(id);
      setWorkflow(updated);
    } catch {
      // handle error
    }
  };

  const handleExecute = async () => {
    if (!id) return;
    try {
      await workflowApi.execute(id);
      navigate('/executions');
    } catch {
      // handle error
    }
  };

  const handleDeleteSelected = () => {
    setNodes((nds) => nds.filter((n) => !n.selected));
    setEdges((eds) => {
      const selectedNodeIds = new Set(nodes.filter((n) => n.selected).map((n) => n.id));
      return eds.filter((e) => !selectedNodeIds.has(e.source) && !selectedNodeIds.has(e.target) && !e.selected);
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col -m-6">
      {/* Toolbar */}
      <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center gap-3 flex-shrink-0">
        <button
          onClick={() => navigate('/workflows')}
          className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
        >
          <ArrowLeft className="w-4.5 h-4.5 text-slate-500" />
        </button>

        <div className="flex-1 flex items-center gap-3 min-w-0">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="text-sm font-semibold text-slate-900 border-none outline-none bg-transparent min-w-0 max-w-xs"
            placeholder="Workflow name"
          />
          {workflow?.status && (
            <span
              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                workflow.status === 'published'
                  ? 'bg-emerald-100 text-emerald-700'
                  : workflow.status === 'archived'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-slate-100 text-slate-600'
              }`}
            >
              {workflow.status}
            </span>
          )}
          {dirty && <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" title="Unsaved changes" />}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDeleteSelected}
            className="p-2 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors"
            title="Delete selected"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            Save
          </button>
          {workflow?.status === 'draft' && (
            <button
              onClick={handlePublish}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition"
            >
              <Globe className="w-3.5 h-3.5" />
              Publish
            </button>
          )}
          {workflow?.status === 'published' && (
            <button
              onClick={handleExecute}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition"
            >
              <Play className="w-3.5 h-3.5" />
              Run
            </button>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode={['Backspace', 'Delete']}
          className="bg-slate-50"
        >
          <Background gap={16} size={1} color="#e2e8f0" />
          <Controls position="bottom-right" />
          <MiniMap
            nodeColor="#6366f1"
            maskColor="rgba(241,245,249,0.8)"
            position="bottom-left"
            className="!bg-white !border-slate-200 !rounded-lg"
          />

          {/* Add step button */}
          <Panel position="top-left">
            <div className="relative">
              <button
                onClick={() => setShowPalette(!showPalette)}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-white rounded-lg border border-slate-200 shadow-sm hover:bg-slate-50 transition"
              >
                <Plus className="w-4 h-4 text-indigo-500" />
                Add Step
              </button>

              {showPalette && (
                <div className="absolute top-11 left-0 z-30 w-52 bg-white rounded-xl border border-slate-200 shadow-lg py-2">
                  {TASK_TYPES.map((task) => {
                    const Icon = task.icon;
                    return (
                      <button
                        key={task.type}
                        onClick={() => addNode(task.type)}
                        className="flex items-center gap-2.5 px-3 py-2 w-full hover:bg-slate-50 transition-colors"
                      >
                        <div
                          className="w-6 h-6 rounded flex items-center justify-center"
                          style={{ backgroundColor: `${task.color}15`, color: task.color }}
                        >
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-sm text-slate-700">{task.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </Panel>

          {/* Step count */}
          <Panel position="top-right">
            <div className="px-3 py-1.5 bg-white rounded-lg border border-slate-200 text-xs text-slate-500 shadow-sm">
              {nodes.length} step{nodes.length !== 1 ? 's' : ''} &middot; v{workflow?.version || 1}
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
}
