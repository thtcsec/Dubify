import { useCallback, useEffect, useState } from 'react';
import { Download, Loader2, RefreshCw, Smartphone } from 'lucide-react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import api, { apiOrigin } from '@/lib/api';
import { formatClock } from '@/lib/subtitles';
import { useI18n } from '@/i18n/I18nProvider';

export interface PlannedClip {
  start: number;
  end: number;
  duration: number;
  label: string;
}

export interface ExportedClip {
  index: number;
  label: string;
  start: number;
  end: number;
  duration: number;
  filename: string;
  url: string;
}

interface ClipExportPanelProps {
  jobId: string | null;
}

const PLATFORMS = [
  { id: 'tiktok', max: 60 },
  { id: 'youtube_shorts', max: 60 },
  { id: 'instagram_reels', max: 90 },
  { id: 'custom', max: 60 },
] as const;

export function ClipExportPanel({ jobId }: ClipExportPanelProps) {
  const { t } = useI18n();
  const [platform, setPlatform] = useState<string>('tiktok');
  const [mode, setMode] = useState<'scene' | 'fixed'>('scene');
  const [verticalCrop, setVerticalCrop] = useState(true);
  const [clips, setClips] = useState<PlannedClip[]>([]);
  const [exported, setExported] = useState<ExportedClip[]>([]);
  const [videoDuration, setVideoDuration] = useState(0);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const planClips = useCallback(async () => {
    if (!jobId) return;
    setIsPlanning(true);
    setError(null);
    try {
      const res = await api.get(`/jobs/${jobId}/plan-clips`, {
        params: { platform, mode },
      });
      setClips(res.data.clips || []);
      setVideoDuration(res.data.video_duration || 0);
      setExported([]);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || t.clips.planFailed);
      setClips([]);
    } finally {
      setIsPlanning(false);
    }
  }, [jobId, platform, mode, t.clips.planFailed]);

  useEffect(() => {
    queueMicrotask(() => {
      void planClips();
    });
  }, [planClips]);

  const exportClips = async () => {
    if (!jobId || clips.length === 0) return;
    setIsExporting(true);
    setError(null);
    try {
      const res = await api.post(`/jobs/${jobId}/export-clips`, {
        clips,
        vertical_crop: verticalCrop,
      });
      setExported(res.data.clips || []);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || t.clips.exportFailed);
    } finally {
      setIsExporting(false);
    }
  };

  if (!jobId) {
    return <p className="text-sm text-slate-500 p-4">{t.editor.needCompleted}</p>;
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-pink-400" />
          {t.clips.title}
        </h2>
        <p className="text-sm text-slate-400 mt-1">{t.clips.subtitle}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label className="text-xs text-slate-400">{t.clips.platform}</Label>
          <Select value={platform} onValueChange={setPlatform}>
            <SelectTrigger className="bg-black/40 border-white/10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PLATFORMS.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {t.clips.platforms[p.id as keyof typeof t.clips.platforms]} ({p.max}s)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label className="text-xs text-slate-400">{t.clips.splitMode}</Label>
          <Select value={mode} onValueChange={(v) => setMode(v as 'scene' | 'fixed')}>
            <SelectTrigger className="bg-black/40 border-white/10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="scene">{t.clips.modeScene}</SelectItem>
              <SelectItem value="fixed">{t.clips.modeFixed}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end gap-3 pb-1">
          <Switch checked={verticalCrop} onCheckedChange={setVerticalCrop} id="vertical-crop" />
          <Label htmlFor="vertical-crop" className="text-sm cursor-pointer">
            {t.clips.verticalCrop}
          </Label>
        </div>
        <div className="flex items-end gap-2">
          <Button variant="outline" size="sm" onClick={() => void planClips()} disabled={isPlanning}>
            <RefreshCw className={`w-4 h-4 mr-1 ${isPlanning ? 'animate-spin' : ''}`} />
            {t.clips.refreshPlan}
          </Button>
          <Button
            size="sm"
            className="bg-pink-600 hover:bg-pink-500"
            onClick={() => void exportClips()}
            disabled={isExporting || clips.length === 0}
          >
            {isExporting ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-1" />
            )}
            {isExporting ? t.clips.exporting : t.clips.exportAll}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </div>
      )}

      {videoDuration > 0 && (
        <p className="text-xs text-slate-500">
          {t.clips.sourceDuration}: {formatClock(videoDuration)} · {clips.length} {t.clips.segments}
        </p>
      )}

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {clips.map((clip, i) => (
          <div
            key={`${clip.label}-${i}`}
            className="rounded-lg border border-white/10 bg-black/30 p-3 text-sm"
          >
            <div className="font-medium text-white">{clip.label}</div>
            <div className="text-xs text-slate-400 mt-1 font-mono">
              {formatClock(clip.start)} → {formatClock(clip.end)} ({Math.round(clip.duration)}s)
            </div>
          </div>
        ))}
      </div>

      {exported.length > 0 && (
        <div className="border-t border-white/10 pt-4 space-y-2">
          <h3 className="text-sm font-semibold text-slate-300">{t.clips.downloads}</h3>
          {exported.map((clip) => (
            <a
              key={clip.filename}
              href={`${apiOrigin}${clip.url}`}
              download={clip.filename}
              className="flex items-center justify-between rounded-lg border border-pink-500/20 bg-pink-500/10 px-3 py-2 text-sm hover:bg-pink-500/20 transition-colors"
            >
              <span>
                {clip.label} · {Math.round(clip.duration)}s
              </span>
              <Download className="w-4 h-4 text-pink-300" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
