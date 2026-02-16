/**
 * WorkflowFilesPage — Browse and manage files in a workflow's storage folder.
 *
 * Shows organized view of: results, icons, docs, screenshots, config, logs.
 * Allows upload and download of files.
 */
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  FolderOpen,
  FileText,
  Image,
  Camera,
  BookOpen,
  Settings,
  ScrollText,
  Download,
  Upload,
  RefreshCw,
  File,
  FileJson,
  FileSpreadsheet,
  Loader2,
  FolderPlus,
  ExternalLink,
} from 'lucide-react';
import { storageApi } from '@/api/storage';
import { workflowApi } from '@/api/workflows';

/* ─── Types ─── */
interface StorageFile {
  name: string;
  size: number;
  modified: string;
  path: string;
}

interface WorkflowFiles {
  [subfolder: string]: StorageFile[];
}

/* ─── Subfolder metadata ─── */
const SUBFOLDER_META: Record<string, { label: string; labelBg: string; icon: any; description: string; color: string }> = {
  results: {
    label: 'Резултати',
    labelBg: 'Результаты',
    icon: FileSpreadsheet,
    description: 'Изпълнения — XLSX, CSV, JSON експорти',
    color: 'emerald',
  },
  icons: {
    label: 'Икони',
    labelBg: 'Иконки',
    icon: Image,
    description: 'Икона и миниатюри на процеса',
    color: 'purple',
  },
  screenshots: {
    label: 'Снимки',
    labelBg: 'Скриншоты',
    icon: Camera,
    description: 'Скрийншоти от стъпките на изпълнение',
    color: 'blue',
  },
  docs: {
    label: 'Документация',
    labelBg: 'Документация',
    icon: BookOpen,
    description: 'Обяснения, ръководства, бележки',
    color: 'amber',
  },
  config: {
    label: 'Конфигурация',
    labelBg: 'Конфигурация',
    icon: Settings,
    description: 'Експортирани настройки и шаблони',
    color: 'slate',
  },
  logs: {
    label: 'Логове',
    labelBg: 'Логи',
    icon: ScrollText,
    description: 'Журнали от изпълнения',
    color: 'orange',
  },
  root: {
    label: 'Основни файлове',
    labelBg: 'Основные файлы',
    icon: FileText,
    description: 'README и метаданни',
    color: 'cyan',
  },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'json': return FileJson;
    case 'xlsx': case 'csv': return FileSpreadsheet;
    case 'png': case 'jpg': case 'jpeg': case 'gif': case 'svg': return Image;
    case 'md': case 'txt': return FileText;
    default: return File;
  }
}

/* ─── Main Component ─── */
export default function WorkflowFilesPage() {
  const { id: workflowId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [workflowName, setWorkflowName] = useState('');
  const [folderName, setFolderName] = useState('');
  const [files, setFiles] = useState<WorkflowFiles>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState<string | null>(null);

  const loadFiles = useCallback(async () => {
    if (!workflowId) return;
    setLoading(true);
    try {
      const resp = await storageApi.listFiles(workflowId);
      setFiles(resp.data.files || {});
      setWorkflowName(resp.data.workflow_name || '');
      setFolderName(resp.data.folder || '');
      setError('');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load files');
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const handleUpload = async (subfolder: string, file: File) => {
    if (!workflowId) return;
    setUploading(subfolder);
    try {
      await storageApi.uploadFile(workflowId, subfolder, file);
      await loadFiles();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(null);
    }
  };

  const totalFiles = Object.values(files).reduce((sum, arr) => sum + arr.length, 0);
  const totalSize = Object.values(files).flat().reduce((sum, f) => sum + f.size, 0);

  // Order subfolders: results first, then icons, screenshots, docs, config, logs, root
  const orderedSubfolders = ['results', 'icons', 'screenshots', 'docs', 'config', 'logs', 'root'];
  const subfolders = orderedSubfolders.filter(sf => files[sf]?.length > 0 || sf !== 'root');

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600 dark:text-slate-300" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-indigo-500" />
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                {workflowName || 'Workflow Files'}
              </h1>
            </div>
            {folderName && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 font-mono">
                📁 storage/workflows/{folderName}/
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/workflows/${workflowId}/edit`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/20 rounded-lg transition"
            >
              <ExternalLink className="w-4 h-4" />
              Редактор
            </Link>
            <button
              onClick={loadFiles}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Обнови
            </button>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-6 py-3 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-6 text-sm">
          <span className="text-slate-500">
            <strong className="text-slate-900 dark:text-white">{totalFiles}</strong> файла
          </span>
          <span className="text-slate-500">
            <strong className="text-slate-900 dark:text-white">{formatFileSize(totalSize)}</strong> общо
          </span>
          <span className="text-slate-500">
            <strong className="text-slate-900 dark:text-white">{Object.keys(files).filter(k => (files[k]?.length || 0) > 0).length}</strong> папки с файлове
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        </div>
      )}

      {/* Folder Grid */}
      {!loading && (
        <div className="px-6 py-6 space-y-6">
          {subfolders.map(subfolder => {
            const meta = SUBFOLDER_META[subfolder] || {
              label: subfolder,
              icon: FolderOpen,
              description: '',
              color: 'slate',
            };
            const Icon = meta.icon;
            const folderFiles = files[subfolder] || [];
            const canUpload = ['icons', 'docs', 'config', 'screenshots'].includes(subfolder);

            const colorClasses: Record<string, string> = {
              emerald: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
              purple: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
              blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
              amber: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
              slate: 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700',
              orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
              cyan: 'bg-cyan-50 dark:bg-cyan-900/20 border-cyan-200 dark:border-cyan-800',
            };

            const iconColorClasses: Record<string, string> = {
              emerald: 'text-emerald-600 dark:text-emerald-400',
              purple: 'text-purple-600 dark:text-purple-400',
              blue: 'text-blue-600 dark:text-blue-400',
              amber: 'text-amber-600 dark:text-amber-400',
              slate: 'text-slate-600 dark:text-slate-400',
              orange: 'text-orange-600 dark:text-orange-400',
              cyan: 'text-cyan-600 dark:text-cyan-400',
            };

            return (
              <div
                key={subfolder}
                className={`rounded-xl border ${colorClasses[meta.color] || colorClasses.slate} overflow-hidden`}
              >
                {/* Folder header */}
                <div className="px-5 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className={`w-5 h-5 ${iconColorClasses[meta.color] || ''}`} />
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white text-sm">
                        {meta.label}
                        {folderFiles.length > 0 && (
                          <span className="ml-2 text-xs font-normal text-slate-500">
                            ({folderFiles.length} {folderFiles.length === 1 ? 'файл' : 'файла'})
                          </span>
                        )}
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{meta.description}</p>
                    </div>
                  </div>
                  {canUpload && (
                    <label className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 border border-slate-200 dark:border-slate-600 rounded-lg cursor-pointer transition">
                      {uploading === subfolder ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Upload className="w-3.5 h-3.5" />
                      )}
                      Качи файл
                      <input
                        type="file"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) handleUpload(subfolder, f);
                          e.target.value = '';
                        }}
                      />
                    </label>
                  )}
                </div>

                {/* File list */}
                {folderFiles.length > 0 ? (
                  <div className="border-t border-slate-200/50 dark:border-slate-700/50">
                    <table className="w-full text-sm">
                      <tbody>
                        {folderFiles.map((file, idx) => {
                          const FileIcon = getFileIcon(file.name);
                          return (
                            <tr
                              key={file.path}
                              className={`${idx % 2 === 0 ? 'bg-white/50 dark:bg-slate-800/50' : ''} hover:bg-white dark:hover:bg-slate-700/50 transition`}
                            >
                              <td className="px-5 py-2.5 flex items-center gap-2">
                                <FileIcon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                <span className="font-mono text-slate-700 dark:text-slate-300 truncate">
                                  {file.name}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-right text-slate-500 text-xs whitespace-nowrap">
                                {formatFileSize(file.size)}
                              </td>
                              <td className="px-3 py-2.5 text-right text-slate-500 text-xs whitespace-nowrap">
                                {formatDate(file.modified)}
                              </td>
                              <td className="px-5 py-2.5 text-right">
                                <a
                                  href={storageApi.getFileUrl(file.path)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/20 rounded transition"
                                >
                                  <Download className="w-3.5 h-3.5" />
                                  Свали
                                </a>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="px-5 py-4 text-center text-sm text-slate-400 dark:text-slate-500 border-t border-slate-200/50 dark:border-slate-700/50">
                    Няма файлове
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
