import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  History as HistoryIcon, Shield, HardDrive, Globe,
  Eye, EyeOff, Loader2, CheckCircle2, XCircle, Clock,
  PauseCircle, Ban, RefreshCw
} from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import api from '@/lib/api';
import { useJobEvents } from '@/lib/jobEvents';
import { useI18n } from '@/i18n/I18nProvider';
import { DeleteAllJobsButton } from '@/components/jobs/DeleteAllJobsButton';
import {
  engineModeToPreset,
  presetToEngineMode,
  type ProcessingPreset,
} from '@/lib/processingPreset';

// ─── History View (Real data from /jobs endpoint) ───────────────────────────

interface Job {
  id: string;
  filename: string;
  type: string;
  status: string;
  progress?: number;
  message: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  output_path: string | null;
}

interface JobsResponse {
  jobs: Job[];
  total: number;
}

interface SettingsResponse {
  project_name: string;
  base_dir: string;
  storage_dir: string;
  models_dir: string;
  processing_engine: 'local' | 'cloud';
  processing_mode: 'offline' | 'hybrid' | 'online';
  capabilities?: {
    cloud_llm: boolean;
    network_tts: boolean;
    url_import: boolean;
  };
  cloud_status?: {
    ready: boolean;
    configured_providers: string[];
    message: string;
  };
  local_tts_status?: {
    ready: boolean;
    engine: string;
    available_models: string[];
    message: string;
  };
  whisper_model: string;
  nllb_model: string;
  llm_model: string;
  llm_models: Array<{
    id: string;
    name: string;
    tier: string;
    best_for: string;
    speed?: string;
    provider: string;
  }>;
  openai_api_key: string;
  anthropic_api_key: string;
  gemini_api_key: string;
  groq_api_key: string;
  keys_configured: Record<string, boolean>;
}

type SettingsApiKeyField = 'openai_api_key' | 'anthropic_api_key' | 'gemini_api_key' | 'groq_api_key';

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function statusIcon(status: string) {
  switch (status) {
    case 'completed': return <CheckCircle2 className="w-4 h-4 text-green-400" />;
    case 'failed': return <XCircle className="w-4 h-4 text-red-400" />;
    case 'processing': return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
    case 'cancelled': return <Ban className="w-4 h-4 text-orange-400" />;
    case 'paused': return <PauseCircle className="w-4 h-4 text-yellow-400" />;
    default: return <Clock className="w-4 h-4 text-slate-400" />;
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'completed': return 'bg-green-500/10 text-green-400';
    case 'failed': return 'bg-red-500/10 text-red-400';
    case 'processing': return 'bg-blue-500/10 text-blue-400';
    case 'cancelled': return 'bg-orange-500/10 text-orange-400';
    case 'paused': return 'bg-yellow-500/10 text-yellow-400';
    default: return 'bg-slate-500/10 text-slate-400';
  }
}

export function HistoryView() {
  const { t } = useI18n();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [offset, setOffset] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const limit = 20;

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: { limit: number; offset: number; status?: string } = { limit, offset };
      if (statusFilter !== 'all') params.status = statusFilter;
      const response = await api.get<JobsResponse>('/jobs', { params });
      setJobs(response.data.jobs || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Failed to fetch job history', error);
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset, statusFilter]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void fetchJobs();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [fetchJobs]);

  useJobEvents<Job>((payload) => {
    const nextJob = payload.job;
    setJobs((currentJobs) => {
      const existingIndex = currentJobs.findIndex((job) => job.id === nextJob.id);
      if (existingIndex >= 0) {
        const updated = [...currentJobs];
        updated[existingIndex] = nextJob;
        return updated;
      }
      const includeByStatus = statusFilter === 'all' || nextJob.status === statusFilter;
      if (offset === 0 && includeByStatus) {
        return [nextJob, ...currentJobs].slice(0, limit);
      }
      return currentJobs;
    });
    setSelectedJob((current) => (current?.id === nextJob.id ? nextJob : current));
    setTotal((value) => value + (payload.type === 'created' ? 1 : 0));
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">
            <span className="bg-gradient-to-br from-blue-500 to-indigo-500 text-transparent bg-clip-text">
              {t.history.title}
            </span>
          </h1>
          <p className="text-slate-400">{t.history.subtitle}</p>
        </div>
        <div className="flex items-center gap-3">
          <DeleteAllJobsButton scope="all" variant="history" onDeleted={fetchJobs} />
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setOffset(0); }}>
            <SelectTrigger className="w-[140px] bg-white/5 border-white/10">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="icon" onClick={fetchJobs} title="Refresh">
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <div className="relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
        <Card className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden rounded-2xl">
          <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <HistoryIcon className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>{t.history.empty}</p>
            </div>
          ) : (
            jobs.map((job, i) => (
              <button
                type="button"
                key={job.id}
                onClick={() => setSelectedJob(job)}
                className={`w-full p-4 flex gap-4 items-start text-left transition-colors hover:bg-white/5 ${i !== jobs.length - 1 ? 'border-b border-white/5' : ''}`}
              >
                <div className={`p-2 rounded-full ${statusColor(job.status)}`}>
                  {statusIcon(job.status)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-sm truncate">{job.filename || 'Untitled'}</h4>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                        {job.type || 'dubbing'}
                      </Badge>
                    </div>
                    <span className="text-[10px] text-slate-500 shrink-0 ml-2">{timeAgo(job.created_at)}</span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">
                    {job.status === 'failed' && job.error ? `Error: ${job.error}` :
                     job.message || `Status: ${job.status}`}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-1">
                    Progress: {typeof job.progress === 'number' ? `${job.progress}%` : 'N/A'}
                  </p>
                  <p className="text-[10px] text-slate-600 font-mono mt-1">{job.id}</p>
                </div>
                <Badge className={`shrink-0 text-[10px] ${statusColor(job.status)}`}>
                  {job.status.toUpperCase()}
                </Badge>
              </button>
            ))
          )}
        </CardContent>
      </Card>
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Showing {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
              Next
            </Button>
          </div>
        </div>
      )}

      <Dialog open={Boolean(selectedJob)} onOpenChange={(open) => !open && setSelectedJob(null)}>
        <DialogContent className="border-white/10 bg-slate-950 text-white sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Job Details</DialogTitle>
          </DialogHeader>
          {selectedJob && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-3">
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Filename</Label>
                  <p className="mt-1 text-slate-100 break-all">{selectedJob.filename}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Status</Label>
                  <p className="mt-1">{selectedJob.status}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Progress</Label>
                  <p className="mt-1">{typeof selectedJob.progress === 'number' ? `${selectedJob.progress}%` : 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Type</Label>
                  <p className="mt-1">{selectedJob.type}</p>
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Created</Label>
                  <p className="mt-1">{new Date(selectedJob.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Updated</Label>
                  <p className="mt-1">{new Date(selectedJob.updated_at).toLocaleString()}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Started / Completed</Label>
                  <p className="mt-1">{selectedJob.started_at ? new Date(selectedJob.started_at).toLocaleString() : 'Not started'}</p>
                  <p className="mt-1">{selectedJob.completed_at ? new Date(selectedJob.completed_at).toLocaleString() : 'Not completed'}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Output</Label>
                  <p className="mt-1 break-all text-slate-300">{selectedJob.output_path || 'No output yet'}</p>
                </div>
              </div>
              <div className="md:col-span-2 space-y-3">
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Message</Label>
                  <p className="mt-1 text-slate-300">{selectedJob.message || 'No message'}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Error</Label>
                  <p className="mt-1 text-red-300">{selectedJob.error || 'No error'}</p>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-slate-500">Job ID</Label>
                  <p className="mt-1 font-mono break-all text-slate-400">{selectedJob.id}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Settings View (with Gemini + Groq keys) ───────────────────────────────

export function SettingsView() {
  const { t } = useI18n();
  const [config, setConfig] = useState<SettingsResponse | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [groqKey, setGroqKey] = useState("");
  const [llmModel, setLlmModel] = useState("auto");
  const [processingPreset, setProcessingPreset] = useState<ProcessingPreset>('hybrid');
  const [saveWarning, setSaveWarning] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchConfig = async () => {
      try {
        const response = await api.get<SettingsResponse>('/settings');
        if (mounted) {
          setConfig(response.data);
          setOpenaiKey(response.data.openai_api_key || "");
          setAnthropicKey(response.data.anthropic_api_key || "");
          setGeminiKey(response.data.gemini_api_key || "");
          setGroqKey(response.data.groq_api_key || "");
          setLlmModel(response.data.llm_model || "auto");
          setProcessingPreset(
            engineModeToPreset(response.data.processing_engine, response.data.processing_mode),
          );
        }
      } catch (error) {
        console.error('Failed to fetch config', error);
      }
    };
    fetchConfig();
    return () => { mounted = false; };
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const { processing_engine, processing_mode } = presetToEngineMode(processingPreset);
      const saveResponse = await api.post<{ warning?: string | null }>('/settings', {
        processing_engine,
        processing_mode,
        openai_api_key: openaiKey,
        anthropic_api_key: anthropicKey,
        gemini_api_key: geminiKey,
        groq_api_key: groqKey,
        llm_model: llmModel,
      });
      setSaveWarning(saveResponse.data.warning || null);
      // Refresh config from server to get masked values
      const response = await api.get<SettingsResponse>('/settings');
      setConfig(response.data);
      setOpenaiKey(response.data.openai_api_key || "");
      setAnthropicKey(response.data.anthropic_api_key || "");
      setGeminiKey(response.data.gemini_api_key || "");
      setGroqKey(response.data.groq_api_key || "");
      setLlmModel(response.data.llm_model || "auto");
      setProcessingPreset(
        engineModeToPreset(response.data.processing_engine, response.data.processing_mode),
      );
      setIsEditing(false);
    } catch {
      alert(t.settings.saveFailed);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleShow = (key: string) => setShowKeys(prev => ({ ...prev, [key]: !prev[key] }));

  const API_KEY_FIELDS = [
    { id: 'openai', configKey: 'openai_api_key' as SettingsApiKeyField, label: 'OpenAI API Key', placeholder: 'sk-...', value: openaiKey, setter: setOpenaiKey },
    { id: 'anthropic', configKey: 'anthropic_api_key' as SettingsApiKeyField, label: 'Anthropic API Key', placeholder: 'sk-ant-...', value: anthropicKey, setter: setAnthropicKey },
    { id: 'gemini', configKey: 'gemini_api_key' as SettingsApiKeyField, label: 'Google Gemini API Key', placeholder: 'AIza...', value: geminiKey, setter: setGeminiKey },
    { id: 'groq', configKey: 'groq_api_key' as SettingsApiKeyField, label: 'Groq API Key', placeholder: 'gsk_...', value: groqKey, setter: setGroqKey },
  ];
  const cloudStatusReady = Boolean(config?.cloud_status?.ready);
  const cloudStatusMessage = config?.cloud_status?.message || 'Cloud status is unavailable. Refresh after the backend loads the latest settings API.';
  const localTtsReady = Boolean(config?.local_tts_status?.ready);
  const localTtsMessage = config?.local_tts_status?.message || 'Offline TTS status is unavailable.';
  const localTtsModelCount = config?.local_tts_status?.available_models?.length || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">
          <span className="bg-gradient-to-br from-indigo-500 to-purple-500 text-transparent bg-clip-text">{t.settings.title}</span>
        </h1>
        <p className="text-slate-400">{t.settings.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Environment Paths */}
        <div className="relative group lg:col-span-2">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
          <Card className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden rounded-2xl h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg"><HardDrive className="w-5 h-5 text-primary" /> {t.settings.envPaths}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-[10px] uppercase text-slate-500">Project Root</Label>
                <p className="text-xs font-mono bg-black/20 p-2 rounded truncate">{config?.base_dir}</p>
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase text-slate-500">Storage Directory</Label>
                <p className="text-xs font-mono bg-black/20 p-2 rounded truncate">{config?.storage_dir}</p>
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase text-slate-500">Models Directory</Label>
                <p className="text-xs font-mono bg-black/20 p-2 rounded truncate">{config?.models_dir}</p>
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase text-slate-500">Project Name</Label>
                <p className="text-xs font-mono bg-black/20 p-2 rounded">{config?.project_name}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        </div>

        {/* AI Models */}
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/10 to-teal-500/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
          <Card className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden rounded-2xl h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg"><Globe className="w-5 h-5 text-primary" /> {t.settings.defaultModels}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-[10px] uppercase text-slate-500">{t.settings.presetLabel}</Label>
              <Select
                value={processingPreset}
                onValueChange={(value: ProcessingPreset) => setProcessingPreset(value)}
                disabled={!isEditing}
              >
                <SelectTrigger className="bg-black/20 border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hybrid">{t.settings.presets.hybrid.label}</SelectItem>
                  <SelectItem value="local_offline">{t.settings.presets.local_offline.label}</SelectItem>
                  <SelectItem value="cloud_online">{t.settings.presets.cloud_online.label}</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[10px] text-slate-500">
                {processingPreset === 'local_offline'
                  ? t.settings.presets.local_offline.desc
                  : processingPreset === 'cloud_online'
                    ? t.settings.presets.cloud_online.desc
                    : t.settings.presets.hybrid.desc}
              </p>
              <p className="text-[10px] text-slate-600">{t.settings.presetHint}</p>
              {config?.capabilities && (
                <div className="grid grid-cols-3 gap-2 text-[10px] text-slate-500">
                  <div>{t.settings.capLlm}: {config.capabilities.cloud_llm ? t.common.on : t.common.off}</div>
                  <div>{t.settings.capTts}: {config.capabilities.network_tts ? t.common.on : t.common.off}</div>
                  <div>{t.settings.capUrl}: {config.capabilities.url_import ? t.common.on : t.common.off}</div>
                </div>
              )}
            </div>
            <div className={`rounded-lg border px-3 py-2 text-[10px] ${
              cloudStatusReady
                ? 'border-green-500/20 bg-green-500/10 text-green-300'
                : 'border-yellow-500/20 bg-yellow-500/10 text-yellow-200'
            }`}>
              <div className="font-semibold">
                Cloud Status: {cloudStatusReady ? 'Ready' : 'Missing Keys'}
              </div>
              <div>{cloudStatusMessage}</div>
            </div>
            <div className={`rounded-lg border px-3 py-2 text-[10px] ${
              localTtsReady
                ? 'border-green-500/20 bg-green-500/10 text-green-300'
                : 'border-yellow-500/20 bg-yellow-500/10 text-yellow-200'
            }`}>
              <div className="font-semibold">
                Offline TTS: {localTtsReady ? 'Ready' : 'Not Ready'}
              </div>
              <div>{localTtsMessage}</div>
              <div className="mt-1 text-[10px] opacity-80">
                Engine: {config?.local_tts_status?.engine || 'piper'} · Models: {localTtsModelCount}
              </div>
            </div>
            {saveWarning && (
              <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/10 px-3 py-2 text-[10px] text-yellow-200">
                {saveWarning}
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-[10px] uppercase text-slate-500">Whisper ASR</Label>
              <p className="text-sm font-semibold">{config?.whisper_model}</p>
            </div>
            <div className="space-y-1">
              <Label className="text-[10px] uppercase text-slate-500">NLLB Translation</Label>
              <p className="text-sm font-semibold truncate">{config?.nllb_model}</p>
            </div>
            <div className="space-y-2 pt-2 border-t border-white/10">
              <Label className="text-[10px] uppercase text-slate-500">{t.settings.llmModel}</Label>
              <Select value={llmModel} onValueChange={setLlmModel} disabled={!isEditing}>
                <SelectTrigger className="bg-black/20 border-white/10 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  <SelectItem value="auto">Auto (first available key)</SelectItem>
                  {(config?.llm_models || []).map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name} — {m.tier}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {(() => {
                const sel = config?.llm_models?.find((m) => m.id === llmModel);
                if (!sel) return <p className="text-[10px] text-slate-500">{t.settings.llmModelHint}</p>;
                return (
                  <p className="text-[10px] text-slate-400 leading-snug">
                    <span className="text-cyan-300/90">{sel.tier}</span> · {sel.best_for}
                    {sel.speed ? ` · ${sel.speed}` : ''}
                  </p>
                );
              })()}
            </div>
          </CardContent>
        </Card>
        </div>

        {/* API Keys — All 4 providers */}
        <div className="relative group lg:col-span-3">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
          <Card className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden rounded-2xl">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg"><Shield className="w-5 h-5 text-primary" /> AI Provider API Keys</CardTitle>
            <div className="flex gap-2">
              {isEditing ? (
                <>
                  <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)} disabled={isSaving} className="text-slate-400 hover:text-white hover:bg-white/10">Cancel</Button>
                  <Button size="sm" onClick={handleSave} disabled={isSaving} className="btn-glow bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-[0_0_15px_rgba(79,70,229,0.3)]">
                    {isSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Save to .env
                  </Button>
                </>
              ) : (
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)} className="border-white/10 bg-white/5 hover:bg-white/10 text-white">Edit Keys</Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-xs text-slate-500">
              These keys are loaded from your root <code className="text-primary">.env</code> file.
              {isEditing ? " Editing will directly overwrite them." : " Click Edit Keys to modify."}
              {config?.keys_configured && (
                <span className="ml-2">
                  Configured: {Object.entries(config.keys_configured)
                    .filter(([, v]) => Boolean(v))
                    .map(([k]) => k)
                    .join(', ') || 'None'}
                </span>
              )}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {API_KEY_FIELDS.map((field) => (
                <div key={field.id} className="space-y-2">
                  <Label className="text-xs text-slate-400">{field.label}</Label>
                  <div className="relative group">
                    <input
                      type={showKeys[field.id] ? "text" : "password"}
                      readOnly={!isEditing}
                      value={isEditing ? field.value : (config?.[field.configKey] || "")}
                      onChange={(e) => field.setter(e.target.value)}
                      className={`w-full bg-black/40 border rounded-lg px-4 py-3 pr-12 text-xs font-mono outline-none transition-colors ${
                        isEditing ? 'border-primary/50 text-white' : 'border-white/5 text-slate-300'
                      }`}
                      placeholder={field.placeholder}
                    />
                    <button
                      onClick={() => toggleShow(field.id)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-2 hover:bg-white/5 rounded-md transition-colors"
                    >
                      {showKeys[field.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {config?.keys_configured && (
                    <p className={`text-[10px] ${config.keys_configured[field.id] ? 'text-green-500' : 'text-slate-600'}`}>
                      {config.keys_configured[field.id] ? '✓ Configured' : '○ Not set'}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        </div>
      </div>
    </div>
  );
}
