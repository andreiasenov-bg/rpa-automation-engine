import { useCallback, useEffect, useState, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  type EdgeTypes,
  type ReactFlowInstance,
  Handle,
  Position,
  Panel,
  BaseEdge,
  getSmoothStepPath,
  type EdgeProps,
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
  Variable,
  Undo2,
  Redo2,
  Keyboard,
  X,
} from 'lucide-react';
import { workflowApi } from '@/api/workflows';
import WorkflowVariablesPanel from '@/components/WorkflowVariablesPanel';
import StepConfigEditor from '@/components/StepConfigEditor';
import ExecutionRunDialog from '@/components/ExecutionRunDialog';
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

/* ─── Custom smooth-step edge with delete button ─── */
function CustomEdge({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd, selected,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, borderRadius: 16,
  });

  return (
    <g className="group">
      {/* Wider invisible path for easier selection */}
      <path d={edgePath} fill="none" strokeWidth={14} stroke="transparent" className="cursor-pointer" />
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          strokeWidth: selected ? 3 : 2,
          stroke: selected ? '#6366f1' : '#94a3b8',
          transition: 'stroke 0.15s, stroke-width 0.15s',
        }}
      />
      {/* Delete button on hover */}
      <foreignObject
        x={labelX - 10} y={labelY - 10} width={20} height={20}
        className="opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none group-hover:pointer-events-auto"
      >
        <button
          className="w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center text-[10px] shadow-sm hover:bg-red-600 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            const event = new CustomEvent('delete-edge', { detail: id });
            window.dispatchEvent(event);
          }}
          title="Remove connection"
        >
          <X className="w-3 h-3" />
        </button>
      </foreignObject>
    </g>
  );
}

const edgeTypes: EdgeTypes = { custom: CustomEdge };

/* ─── Custom node component ─── */
function StepNode({ data, selected }: { data: { label: string; type: string; color: string }; selected?: boolean }) {
  const taskDef = TASK_TYPES.find((t) => t.type === data.type);
  const Icon = taskDef?.icon || Code2;
  const color = data.color || taskDef?.color || '#6366f1';

  return (
    <div
      className={`bg-white rounded-xl border-2 shadow-sm min-w-[160px] transition-shadow ${selected ? 'shadow-lg ring-2 ring-indigo-200' : ''}`}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white hover:!bg-indigo-500 hover:!scale-125 transition-all" />
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
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white hover:!bg-indigo-500 hover:!scale-125 transition-all" />
    </div>
  );
}

const nodeTypes: NodeTypes = { stepNode: StepNode };

/* ─── Undo/Redo hook ─── */
interface FlowSnapshot {
  nodes: Node[];
  edges: Edge[];
}

function useUndoRedo(maxHistory = 50) {
  const past = useRef<FlowSnapshot[]>([]);
  const future = useRef<FlowSnapshot[]>([]);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const push = useCallback((snapshot: FlowSnapshot) => {
    past.current.push(snapshot);
    if (past.current.length > maxHistory) past.current.shift();
    future.current = [];
    setCanUndo(true);
    setCanRedo(false);
  }, [maxHistory]);

  const undo = useCallback((current: FlowSnapshot): FlowSnapshot | null => {
    if (past.current.length === 0) return null;
    const prev = past.current.pop()!;
    future.current.push(current);
    setCanUndo(past.current.length > 0);
    setCanRedo(true);
    return prev;
  }, []);

  const redo = useCallback((current: FlowSnapshot): FlowSnapshot | null => {
    if (future.current.length === 0) return null;
    const next = future.current.pop()!;
    past.current.push(current);
    setCanUndo(true);
    setCanRedo(future.current.length > 0);
    return next;
  }, []);

  return { push, undo, redo, canUndo, canRedo };
}

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
          type: 'custom',
          animated: true,
          markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: '#94a3b8' },
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

/* ─── Default edge options ─── */
const defaultEdgeOptions = {
  type: 'custom',
  animated: true,
  markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: '#94a3b8' },
  style: { stroke: '#94a3b8', strokeWidth: 2 },
};

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
  const [showVariables, setShowVariables] = useState(false);
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [showRunDialog, setShowRunDialog] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const counterRef = useRef(0);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;

  const history = useUndoRedo();

  // Snapshot before mutations
  const snapshot = useCallback(() => {
    history.push({ nodes: structuredClone(nodesRef.current), edges: structuredClone(edgesRef.current) });
  }, [history]);

  const handleUndo = useCallback(() => {
    const prev = history.undo({ nodes: nodesRef.current, edges: edgesRef.current });
    if (prev) { setNodes(prev.nodes); setEdges(prev.edges); }
  }, [history, setNodes, setEdges]);

  const handleRedo = useCallback(() => {
    const next = history.redo({ nodes: nodesRef.current, edges: edgesRef.current });
    if (next) { setNodes(next.nodes); setEdges(next.edges); }
  }, [history, setNodes, setEdges]);

  // Listen for edge delete events from custom edge component
  useEffect(() => {
    const handler = (e: Event) => {
      const edgeId = (e as CustomEvent).detail;
      snapshot();
      setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));
    };
    window.addEventListener('delete-edge', handler);
    return () => window.removeEventListener('delete-edge', handler);
  }, [setEdges, snapshot]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      // Ignore if inside input/textarea
      if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;

      if (mod && e.key === 'z' && !e.shiftKey) { e.preventDefault(); handleUndo(); }
      if (mod && e.key === 'z' && e.shiftKey) { e.preventDefault(); handleRedo(); }
      if (mod && e.key === 'y') { e.preventDefault(); handleRedo(); }
      if (mod && e.key === 's') { e.preventDefault(); handleSaveRef.current(); }
      if (e.key === 'Escape') { setSelectedStep(null); setShowPalette(false); setShowShortcuts(false); }
      if (e.key === '?' && !mod) { setShowShortcuts((v) => !v); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleUndo, handleRedo]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, navigate]);

  // Track changes
  useEffect(() => {
    if (workflow) setDirty(true);
  }, [nodes, edges, name, description]);

  const onConnect = useCallback(
    (params: Connection) => {
      snapshot();
      setEdges((eds) => addEdge({ ...params, ...defaultEdgeOptions }, eds));
    },
    [setEdges, snapshot],
  );

  const addNode = useCallback((taskType: string, position?: { x: number; y: number }) => {
    snapshot();
    counterRef.current += 1;
    const taskDef = TASK_TYPES.find((t) => t.type === taskType)!;
    const newNode: Node = {
      id: `step_${Date.now()}_${counterRef.current}`,
      type: 'stepNode',
      position: position || { x: 250, y: nodesRef.current.length * 120 + 50 },
      data: {
        label: `${taskDef.label} ${counterRef.current}`,
        type: taskType,
        config: {},
        color: taskDef.color,
      },
    };
    setNodes((nds) => [...nds, newNode]);
    setShowPalette(false);
    return newNode;
  }, [setNodes, snapshot]);

  /* ─── Find closest node to auto-connect ─── */
  const findClosestNodeAbove = useCallback((position: { x: number; y: number }, excludeId: string): Node | null => {
    let closest: Node | null = null;
    let minDist = 150; // Max snap distance
    for (const node of nodesRef.current) {
      if (node.id === excludeId) continue;
      // Only connect to nodes above the drop position
      if (node.position.y >= position.y) continue;
      const dx = node.position.x - position.x;
      const dy = (node.position.y + 60) - position.y; // offset for node height
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < minDist) {
        minDist = dist;
        closest = node;
      }
    }
    return closest;
  }, []);

  const handleSave = useCallback(async () => {
    if (!id || !workflow) return;
    setSaving(true);
    try {
      const steps = nodesEdgesToSteps(nodesRef.current, edgesRef.current);
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
  }, [id, workflow, name, description]);
  const handleSaveRef = useRef(handleSave);
  handleSaveRef.current = handleSave;

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

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedStep(node.id);
  }, []);

  const handleStepConfigSave = useCallback((stepId: string, updates: { label: string; config: Record<string, unknown>; on_error?: string }) => {
    snapshot();
    setNodes((nds) =>
      nds.map((n) =>
        n.id === stepId
          ? { ...n, data: { ...n.data, label: updates.label, config: updates.config } }
          : n
      )
    );
  }, [setNodes, snapshot]);

  // Drag & drop from palette to canvas
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const taskType = event.dataTransfer.getData('application/rpa-task-type');
      if (!taskType || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode = addNode(taskType, position);

      // Auto-connect: find closest node above and create edge
      const closest = findClosestNodeAbove(position, newNode.id);
      if (closest) {
        setEdges((eds) =>
          addEdge({ id: `e-${closest.id}-${newNode.id}`, source: closest.id, target: newNode.id, ...defaultEdgeOptions }, eds)
        );
      }
    },
    [reactFlowInstance, addNode, findClosestNodeAbove, setEdges],
  );

  // Track node moves for undo
  const onNodesChangeWrapped = useCallback(
    (changes: Parameters<typeof onNodesChange>[0]) => {
      const hasMoveEnd = changes.some((c) => c.type === 'position' && c.dragging === false);
      const hasRemove = changes.some((c) => c.type === 'remove');
      if (hasMoveEnd || hasRemove) snapshot();
      onNodesChange(changes);
    },
    [onNodesChange, snapshot],
  );

  const onEdgesChangeWrapped = useCallback(
    (changes: Parameters<typeof onEdgesChange>[0]) => {
      const hasRemove = changes.some((c) => c.type === 'remove');
      if (hasRemove) snapshot();
      onEdgesChange(changes);
    },
    [onEdgesChange, snapshot],
  );

  const handleDeleteSelected = () => {
    snapshot();
    setNodes((nds) => nds.filter((n) => !n.selected));
    setEdges((eds) => {
      const selectedNodeIds = new Set(nodesRef.current.filter((n) => n.selected).map((n) => n.id));
      return eds.filter((e) => !selectedNodeIds.has(e.source) && !selectedNodeIds.has(e.target) && !e.selected);
    });
  };

  // Memoize connection line style
  const connectionLineStyle = useMemo(() => ({ stroke: '#6366f1', strokeWidth: 2, strokeDasharray: '5 5' }), []);

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

        <div className="flex items-center gap-1.5">
          {/* Undo / Redo */}
          <button
            onClick={handleUndo}
            disabled={!history.canUndo}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Undo (Ctrl+Z)"
          >
            <Undo2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleRedo}
            disabled={!history.canRedo}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Redo (Ctrl+Shift+Z)"
          >
            <Redo2 className="w-4 h-4" />
          </button>

          <div className="w-px h-5 bg-slate-200 mx-1" />

          <button
            onClick={() => setShowVariables(!showVariables)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border transition ${
              showVariables
                ? 'border-indigo-300 bg-indigo-50 text-indigo-600'
                : 'border-slate-200 text-slate-500 hover:bg-slate-50'
            }`}
            title="Workflow Variables"
          >
            <Variable className="w-3.5 h-3.5" />
            Variables
          </button>
          <button
            onClick={handleDeleteSelected}
            className="p-2 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors"
            title="Delete selected (Del)"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowShortcuts(!showShortcuts)}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            title="Keyboard shortcuts (?)"
          >
            <Keyboard className="w-4 h-4" />
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
              onClick={() => setShowRunDialog(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition"
            >
              <Play className="w-3.5 h-3.5" />
              Run
            </button>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChangeWrapped}
          onEdgesChange={onEdgesChangeWrapped}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          defaultEdgeOptions={defaultEdgeOptions}
          connectionLineStyle={connectionLineStyle}
          fitView
          deleteKeyCode={['Backspace', 'Delete']}
          snapToGrid
          snapGrid={[16, 16]}
          className="bg-slate-50"
        >
          <Background gap={16} size={1} color="#e2e8f0" />
          <Controls position="bottom-right" />
          <MiniMap
            nodeColor="#6366f1"
            maskColor="rgba(241,245,249,0.8)"
            position="bottom-left"
            className="!bg-white !border-slate-200 !rounded-lg"
            zoomable
            pannable
          />

          {/* Dockable step palette */}
          <Panel position="top-left">
            <div className="flex flex-col gap-1">
              <button
                onClick={() => setShowPalette(!showPalette)}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-white rounded-lg border border-slate-200 shadow-sm hover:bg-slate-50 transition"
              >
                <Plus className="w-4 h-4 text-indigo-500" />
                {showPalette ? 'Hide' : 'Add Step'}
              </button>

              {showPalette && (
                <div className="w-48 bg-white rounded-xl border border-slate-200 shadow-lg py-2 max-h-[60vh] overflow-y-auto">
                  <p className="px-3 py-1 text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                    Drag to canvas or click
                  </p>
                  {TASK_TYPES.map((task) => {
                    const Icon = task.icon;
                    return (
                      <div
                        key={task.type}
                        draggable
                        role="button"
                        tabIndex={0}
                        onClick={() => addNode(task.type)}
                        onKeyDown={(e) => { if (e.key === 'Enter') addNode(task.type); }}
                        onDragStart={(e) => {
                          e.dataTransfer.setData('application/rpa-task-type', task.type);
                          e.dataTransfer.effectAllowed = 'move';
                        }}
                        className="flex items-center gap-2.5 px-3 py-2 w-full hover:bg-slate-50 transition-colors cursor-grab active:cursor-grabbing select-none"
                      >
                        <div
                          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${task.color}15`, color: task.color }}
                        >
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-xs font-medium text-slate-700">{task.label}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Panel>

          {/* Step count */}
          <Panel position="top-right">
            <div className="px-3 py-1.5 bg-white rounded-lg border border-slate-200 text-xs text-slate-500 shadow-sm">
              {nodes.length} step{nodes.length !== 1 ? 's' : ''} &middot; {edges.length} edge{edges.length !== 1 ? 's' : ''} &middot; v{workflow?.version || 1}
            </div>
          </Panel>
        </ReactFlow>

        {/* Variables panel */}
        {showVariables && id && (
          <WorkflowVariablesPanel workflowId={id} onClose={() => setShowVariables(false)} />
        )}

        {/* Step config editor */}
        {selectedStep && !showVariables && (() => {
          const node = nodes.find((n) => n.id === selectedStep);
          if (!node) return null;
          return (
            <StepConfigEditor
              step={{
                id: node.id,
                label: node.data.label as string,
                type: node.data.type as string,
                config: (node.data.config as Record<string, unknown>) || {},
                color: node.data.color as string,
              }}
              allStepIds={nodes.map((n) => n.id)}
              onSave={handleStepConfigSave}
              onClose={() => setSelectedStep(null)}
            />
          );
        })()}

        {/* Keyboard shortcuts modal */}
        {showShortcuts && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setShowShortcuts(false)}>
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 p-5 w-80" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-800">Keyboard Shortcuts</h3>
                <button onClick={() => setShowShortcuts(false)} className="p-1 rounded hover:bg-slate-100">
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
              <div className="space-y-2 text-xs">
                {[
                  ['Ctrl+S', 'Save workflow'],
                  ['Ctrl+Z', 'Undo'],
                  ['Ctrl+Shift+Z', 'Redo'],
                  ['Delete / Backspace', 'Delete selected'],
                  ['Escape', 'Close panel'],
                  ['?', 'Toggle shortcuts'],
                ].map(([key, desc]) => (
                  <div key={key} className="flex items-center justify-between py-1">
                    <span className="text-slate-500">{desc}</span>
                    <kbd className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] border border-slate-200">{key}</kbd>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Run dialog */}
      {showRunDialog && id && workflow && (
        <ExecutionRunDialog
          workflowId={id}
          workflowName={name}
          onClose={() => setShowRunDialog(false)}
          onStarted={() => { setShowRunDialog(false); navigate('/executions'); }}
        />
      )}
    </div>
  );
}
