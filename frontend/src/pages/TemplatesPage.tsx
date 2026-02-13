import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Loader2,
  BookOpen,
  Layers,
  ArrowRight,
  X,
  Sparkles,
  Clock,
  Tag,
} from 'lucide-react';
import { templatesApi, type TemplateSummary } from '@/api/templates';

/* ─── Difficulty badge ─── */
const DIFFICULTY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  beginner: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  intermediate: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  advanced: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
};

const CATEGORY_LABELS: Record<string, string> = {
  'data-extraction': 'Data Extraction',
  'monitoring': 'Monitoring',
  'browser-automation': 'Browser Automation',
  'reporting': 'Reporting',
  'ai-powered': 'AI Powered',
};

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const c = DIFFICULTY_COLORS[difficulty] || DIFFICULTY_COLORS.beginner;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize border ${c.bg} ${c.text} ${c.border}`}>
      {difficulty}
    </span>
  );
}

/* ─── Template card ─── */
function TemplateCard({
  template,
  onUse,
}: {
  template: TemplateSummary;
  onUse: (t: TemplateSummary) => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md hover:border-indigo-200 transition-all group">
      <div className="flex items-start justify-between mb-3">
        <span className="text-2xl">{template.icon}</span>
        <DifficultyBadge difficulty={template.difficulty} />
      </div>

      <h3 className="text-sm font-semibold text-slate-900 mb-1">{template.name}</h3>
      <p className="text-xs text-slate-500 mb-3 line-clamp-2">{template.description}</p>

      <div className="flex flex-wrap gap-1 mb-3">
        {template.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-500">
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
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition opacity-0 group-hover:opacity-100"
        >
          Use
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

/* ─── Instantiate Modal ─── */
function InstantiateModal({
  template,
  onClose,
  onConfirm,
}: {
  template: TemplateSummary;
  onClose: () => void;
  onConfirm: (name: string, desc: string) => void;
}) {
  const [name, setName] = useState(template.name);
  const [desc, setDesc] = useState(template.description);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-500" />
            Create from Template
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-500 mb-4">
          Creating a new workflow from "{template.name}" template.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Workflow Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
            <textarea
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 resize-none"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(name, desc)}
            disabled={!name.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition"
          >
            Create Workflow
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ─── */
export default function TemplatesPage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateSummary | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const filters: Record<string, string> = {};
      if (search) filters.search = search;
      if (filterCategory) filters.category = filterCategory;
      if (filterDifficulty) filters.difficulty = filterDifficulty;

      const data = await templatesApi.list(filters);
      setTemplates(data.templates || []);
    } catch {
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [search, filterCategory, filterDifficulty]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    templatesApi.categories().then(setCategories).catch(() => {});
  }, []);

  const handleInstantiate = async (name: string, desc: string) => {
    if (!selectedTemplate || creating) return;
    setCreating(true);
    try {
      const result = await templatesApi.instantiate(selectedTemplate.id, name, desc);
      setSelectedTemplate(null);
      navigate(`/workflows/${result.workflow_id}/edit`);
    } catch {
      // handle error
    } finally {
      setCreating(false);
    }
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
            Pre-built automation workflows ready to use
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
          />
        </div>

        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{CATEGORY_LABELS[c] || c}</option>
          ))}
        </select>

        <select
          value={filterDifficulty}
          onChange={(e) => setFilterDifficulty(e.target.value)}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        >
          <option value="">All Levels</option>
          {difficulties.map((d) => (
            <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Template Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : templates.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <BookOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No templates found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {templates.map((t) => (
            <TemplateCard key={t.id} template={t} onUse={setSelectedTemplate} />
          ))}
        </div>
      )}

      {/* Instantiate Modal */}
      {selectedTemplate && (
        <InstantiateModal
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onConfirm={handleInstantiate}
        />
      )}
    </div>
  );
}
