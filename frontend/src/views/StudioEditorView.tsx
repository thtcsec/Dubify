import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Clapperboard,
  Download,
  Eye,
  Film,
  Merge,
  Pause,
  Play,
  Scissors,
  Smartphone,
  Volume2,
  Wand2,
} from 'lucide-react';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ClipExportPanel } from '../components/editor/ClipExportPanel';
import { EditorTimelineScrubber } from '../components/editor/EditorTimelineScrubber';
import { SubtitlePreviewOverlay } from '../components/editor/SubtitlePreviewOverlay';
import api, { apiOrigin } from '../lib/api';
import { DEFAULT_SUBTITLE_STYLE, type SubtitleStyle } from '../lib/subtitleStyle';
import { useJobEvents } from '../lib/jobEvents';
import { useI18n } from '@/i18n/I18nProvider';
import {
  cuesToSrt,
  formatClock,
  parseSrt,
  secondsToSrtTime,
  type SubtitleCue,
} from '@/lib/subtitles';

interface Job {
  id: string;
  filename: string;
  type: string;
  status: string;
  output_path: string | null;
  created_at: string;
  message?: string | null;
}

export function StudioEditorView() {
  const { t } = useI18n();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [cues, setCues] = useState<SubtitleCue[]>([]);
  const [selectedCueId, setSelectedCueId] = useState<number | null>(null);
  const [duration, setDuration] = useState(0);
  const [playhead, setPlayhead] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isBurning, setIsBurning] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [editorTab, setEditorTab] = useState<'subtitles' | 'clips'>('subtitles');
  const [previewBurn, setPreviewBurn] = useState(true);
  const [subStyle, setSubStyle] = useState<SubtitleStyle>(DEFAULT_SUBTITLE_STYLE);
  const [isScrubbing, setIsScrubbing] = useState(false);

  const fetchCompletedJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/jobs', { params: { limit: 100, status: 'completed' } });
      const completed = (response.data.jobs || []).filter((j: Job) => j.output_path);
      setJobs(completed);
      setSelectedJobId((cur) => cur || completed[0]?.id || null);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void fetchCompletedJobs();
    });
  }, [fetchCompletedJobs]);

  useJobEvents<Job>((payload) => {
    const job = payload.job;
    if (job.status !== 'completed' || !job.output_path) return;
    setJobs((prev) => {
      const i = prev.findIndex((j) => j.id === job.id);
      if (i >= 0) {
        const next = [...prev];
        next[i] = job;
        return next;
      }
      return [job, ...prev];
    });
  });

  const selectedJob = useMemo(
    () => jobs.find((j) => j.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  const videoUrl = selectedJob?.output_path
    ? `${apiOrigin}/storage/output/${selectedJob.output_path.split(/[\\/]/).pop()}`
    : null;

  useEffect(() => {
    const load = async () => {
      if (!selectedJobId) {
        setCues([]);
        return;
      }
      try {
        const meta = await api.get(`/jobs/${selectedJobId}/artifacts`);
        const subPath = meta.data.subtitle_path as string | null;
        if (!subPath) {
          setCues([]);
          return;
        }
        const normalized = subPath.replace(/\\/g, '/');
        const storageIdx = normalized.indexOf('/storage/');
        const artifactsIdx = normalized.indexOf('/artifacts/');
        let url: string | null = null;
        if (storageIdx >= 0) url = `${apiOrigin}${normalized.slice(storageIdx)}`;
        else if (artifactsIdx >= 0) url = `${apiOrigin}/storage${normalized.slice(artifactsIdx)}`;
        if (!url) return;
        const text = await (await fetch(url)).text();
        const parsed = parseSrt(text);
        setCues(parsed);
        setSelectedCueId(parsed[0]?.id ?? null);
        setDirty(false);
      } catch (e) {
        console.error(e);
        setCues([]);
      }
    };
    void load();
  }, [selectedJobId]);

  const selectedCue = cues.find((c) => c.id === selectedCueId) ?? null;

  const seekTo = useCallback(
    (sec: number) => {
      const v = videoRef.current;
      const d = duration || v?.duration || 0;
      if (!v || d <= 0) return;
      const t = Math.min(Math.max(sec, 0), d);
      try {
        v.currentTime = t;
      } catch {
        /* ignore */
      }
      setPlayhead(t);
    },
    [duration],
  );

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      void v.play();
      setIsPlaying(true);
    } else {
      v.pause();
      setIsPlaying(false);
    }
  };

  const updateCue = (id: number, patch: Partial<SubtitleCue>) => {
    setCues((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c;
        const next = { ...c, ...patch };
        if (patch.startSec !== undefined) next.start = secondsToSrtTime(next.startSec);
        if (patch.endSec !== undefined) next.end = secondsToSrtTime(next.endSec);
        return next;
      }),
    );
    setDirty(true);
  };

  const splitSelectedCue = () => {
    if (!selectedCue) return;
    const mid = (selectedCue.startSec + selectedCue.endSec) / 2;
    const left: SubtitleCue = {
      ...selectedCue,
      endSec: mid,
      end: secondsToSrtTime(mid),
    };
    const right: SubtitleCue = {
      id: Math.max(...cues.map((c) => c.id), 0) + 1,
      startSec: mid,
      endSec: selectedCue.endSec,
      start: secondsToSrtTime(mid),
      end: selectedCue.end,
      text: selectedCue.text,
    };
    const idx = cues.findIndex((c) => c.id === selectedCue.id);
    const next = [...cues];
    next.splice(idx, 1, left, right);
    setCues(next);
    setSelectedCueId(right.id);
    setDirty(true);
  };

  const mergeWithNext = () => {
    if (!selectedCue) return;
    const idx = cues.findIndex((c) => c.id === selectedCue.id);
    if (idx < 0 || idx >= cues.length - 1) return;
    const a = cues[idx];
    const b = cues[idx + 1];
    const merged: SubtitleCue = {
      ...a,
      endSec: b.endSec,
      end: b.end,
      text: `${a.text}\n${b.text}`.trim(),
    };
    const next = [...cues];
    next.splice(idx, 2, merged);
    setCues(next);
    setSelectedCueId(merged.id);
    setDirty(true);
  };

  const downloadSrt = () => {
    const blob = new Blob([cuesToSrt(cues)], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${selectedJobId ?? 'subtitles'}.srt`;
    a.click();
  };

  const burnRender = async () => {
    if (!selectedJobId || cues.length === 0) return;
    setIsBurning(true);
    setStatusMsg(null);
    try {
      const form = new FormData();
      form.append('srt', cuesToSrt(cues));
      const res = await api.post(`/jobs/${selectedJobId}/burn-subtitles`, form);
      setStatusMsg(`${t.editor.burnSuccess} → ${res.data.filename}`);
      setDirty(false);
      void fetchCompletedJobs();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setStatusMsg(err.response?.data?.detail || t.editor.burnFailed);
    } finally {
      setIsBurning(false);
    }
  };

  const totalDur = duration || 1;

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t.editor.title}</h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">{t.editor.subtitle}</p>
          <p className="text-[11px] text-slate-500 mt-1">{t.editor.refOpenReel}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {dirty && (
            <Badge variant="outline" className="border-amber-500/40 text-amber-200">
              {t.editor.dirty}
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={downloadSrt} disabled={!cues.length}>
            <Download className="w-4 h-4 mr-1" /> {t.editor.exportSrt}
          </Button>
          <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500" onClick={burnRender} disabled={isBurning || !cues.length}>
            <Wand2 className="w-4 h-4 mr-1" /> {isBurning ? t.editor.burning : t.editor.burnRender}
          </Button>
        </div>
      </div>

      {statusMsg && (
        <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-100">
          {statusMsg}
        </div>
      )}

      <Tabs
        value={editorTab}
        onValueChange={(v) => setEditorTab(v as 'subtitles' | 'clips')}
        className="flex flex-1 min-h-0 flex-col gap-2"
      >
        <TabsList className="w-fit bg-black/40 border border-white/10">
          <TabsTrigger value="subtitles" className="text-xs gap-1">
            <Eye className="w-3.5 h-3.5" />
            {t.editor.tabSubtitles}
          </TabsTrigger>
          <TabsTrigger value="clips" className="text-xs gap-1">
            <Smartphone className="w-3.5 h-3.5" />
            {t.editor.tabClips}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="clips" className="flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
          <div className="h-full min-h-[400px] rounded-xl border border-white/10 bg-[#0a0d14] overflow-hidden flex flex-col">
            <ClipExportPanel jobId={selectedJobId} />
            <p className="px-4 pb-3 text-[11px] text-slate-500 shrink-0">{t.clips.tabNote}</p>
          </div>
        </TabsContent>

        <TabsContent value="subtitles" className="flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
      <div className="flex flex-1 min-h-0 gap-3 h-full">
        {/* Project bin */}
        <aside className="w-56 shrink-0 rounded-xl border border-white/10 bg-[#0a0d14] flex flex-col overflow-hidden">
          <div className="border-b border-white/10 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {t.editor.projects}
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {isLoading ? (
              <p className="text-xs text-slate-500 p-2">…</p>
            ) : jobs.length === 0 ? (
              <p className="text-xs text-slate-500 p-2">{t.editor.noProjects}</p>
            ) : (
              jobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => setSelectedJobId(job.id)}
                  className={`w-full rounded-lg px-2 py-2 text-left text-xs transition-colors ${
                    selectedJobId === job.id ? 'bg-indigo-500/20 text-white' : 'hover:bg-white/5 text-slate-300'
                  }`}
                >
                  <div className="font-medium truncate">{job.filename || job.id}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{job.type}</div>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* Center: preview + timeline */}
        <main className="flex flex-1 min-w-0 flex-col gap-2 rounded-xl border border-white/10 bg-[#0a0d14] overflow-hidden">
          {/* Transport */}
          <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2 bg-black/40">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={togglePlay} disabled={!videoUrl}>
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </Button>
            <span className="text-xs font-mono text-slate-300 tabular-nums">
              {formatClock(playhead)} / {formatClock(duration)}
            </span>
            <span className="text-[10px] text-slate-500 ml-2">{t.editor.playhead}</span>
            {videoUrl && (
              <Button variant="ghost" size="sm" className="ml-auto h-8 text-xs" onClick={() => window.open(videoUrl, '_blank')}>
                <Film className="w-3 h-3 mr-1" /> {t.editor.openExternal}
              </Button>
            )}
          </div>

          {/* Preview + burn subtitle overlay */}
          <div className="relative flex-1 min-h-[200px] bg-black flex items-center justify-center overflow-hidden">
            {videoUrl ? (
              <>
                <video
                  ref={videoRef}
                  className="max-h-full max-w-full"
                  src={videoUrl}
                  onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
                  onTimeUpdate={(e) => {
                    if (!isScrubbing) setPlayhead(e.currentTarget.currentTime);
                  }}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
                <SubtitlePreviewOverlay
                  cues={cues}
                  playhead={playhead}
                  enabled={previewBurn}
                  style={subStyle}
                  emptyHint={t.editor.previewEmpty}
                />
                {previewBurn && (
                  <div className="absolute top-2 left-2 rounded-md bg-black/60 px-2 py-0.5 text-[10px] text-cyan-200 border border-cyan-500/30">
                    {t.editor.previewOn}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-500">{t.editor.needCompleted}</p>
            )}
          </div>

          {/* Timeline */}
          <div className="border-t border-white/10 bg-[#06080c] p-3 space-y-2">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{t.editor.timeline}</div>
            <EditorTimelineScrubber
              duration={totalDur}
              playhead={playhead}
              onSeek={seekTo}
              onScrubStart={() => {
                setIsScrubbing(true);
                videoRef.current?.pause();
                setIsPlaying(false);
              }}
              onScrubEnd={() => setIsScrubbing(false)}
            />

            {['video', 'audio', 'subs'].map((track) => (
              <div key={track} className="flex items-center gap-2">
                <div className="w-20 shrink-0 flex items-center gap-1 text-[10px] text-slate-400">
                  {track === 'video' && <Clapperboard className="w-3 h-3" />}
                  {track === 'audio' && <Volume2 className="w-3 h-3" />}
                  {track === 'subs' && <span className="w-3 text-center">CC</span>}
                  {track === 'video' ? t.editor.trackVideo : track === 'audio' ? t.editor.trackAudio : t.editor.trackSubs}
                </div>
                <div className="relative flex-1 h-8 rounded-md bg-slate-900/80 border border-white/5 overflow-hidden">
                  {track === 'video' && (
                    <div className="absolute inset-y-1 left-1 right-1 rounded bg-slate-700/60" />
                  )}
                  {track === 'audio' && (
                    <div className="absolute inset-y-1 left-1 right-1 rounded bg-emerald-900/40 border border-emerald-500/20" />
                  )}
                  {track === 'subs' &&
                    cues.map((cue) => (
                      <button
                        key={cue.id}
                        type="button"
                        title={cue.text}
                        onClick={() => {
                          setSelectedCueId(cue.id);
                          seekTo(cue.startSec);
                        }}
                        className={`absolute top-1 bottom-1 rounded-sm border text-[0px] ${
                          selectedCueId === cue.id
                            ? 'bg-cyan-400/50 border-cyan-300'
                            : 'bg-cyan-500/25 border-cyan-500/40 hover:bg-cyan-400/35'
                        }`}
                        style={{
                          left: `${(cue.startSec / totalDur) * 100}%`,
                          width: `${Math.max(0.8, ((cue.endSec - cue.startSec) / totalDur) * 100)}%`,
                        }}
                      />
                    ))}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-red-400 z-10 pointer-events-none"
                    style={{ left: `${(playhead / totalDur) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </main>

        {/* Inspector */}
        <aside className="w-72 shrink-0 flex flex-col rounded-xl border border-white/10 bg-[#0a0d14] overflow-hidden">
          <div className="border-b border-white/10 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {t.editor.cueList}
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1 max-h-[28vh]">
            {cues.length === 0 ? (
              <p className="text-xs text-slate-500 p-2">{t.editor.noCues}</p>
            ) : (
              cues.map((cue) => (
                <button
                  key={cue.id}
                  type="button"
                  onClick={() => {
                    setSelectedCueId(cue.id);
                    seekTo(cue.startSec);
                  }}
                  className={`w-full rounded-lg px-2 py-1.5 text-left text-xs ${
                    selectedCueId === cue.id ? 'bg-cyan-500/15 border border-cyan-500/30' : 'hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <div className="font-mono text-[10px] text-slate-500">
                    {cue.start} → {cue.end}
                  </div>
                  <div className="truncate text-slate-200">{cue.text}</div>
                </button>
              ))
            )}
          </div>
          <div className="border-t border-white/10 p-3 space-y-3 bg-black/20">
            <div className="flex items-center justify-between">
              <Label className="text-[10px] uppercase text-slate-500">{t.editor.previewOn}</Label>
              <Switch checked={previewBurn} onCheckedChange={setPreviewBurn} />
            </div>
            <p className="text-[10px] text-slate-500 leading-snug">{t.editor.previewHint}</p>
            <div className="space-y-2">
              <Label className="text-[10px] text-slate-400">{t.editor.fontSize}</Label>
              <Slider
                min={70}
                max={130}
                step={5}
                value={[Math.round(subStyle.fontScale * 100)]}
                onValueChange={([v]) => setSubStyle((s) => ({ ...s, fontScale: v / 100 }))}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] text-slate-400">{t.editor.bottomMargin}</Label>
              <Slider
                min={70}
                max={140}
                step={5}
                value={[Math.round(subStyle.marginScale * 100)]}
                onValueChange={([v]) => setSubStyle((s) => ({ ...s, marginScale: v / 100 }))}
              />
            </div>
          </div>
          {selectedCue && (
            <div className="border-t border-white/10 p-3 space-y-3 bg-black/30">
              <label className="text-[10px] uppercase text-slate-500">{t.editor.cueText}</label>
              <textarea
                className="w-full min-h-[80px] rounded-lg border border-white/10 bg-black/50 p-2 text-sm text-slate-100"
                value={selectedCue.text}
                onChange={(e) => updateCue(selectedCue.id, { text: e.target.value })}
              />
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="flex-1 h-8 text-xs" onClick={splitSelectedCue}>
                  <Scissors className="w-3 h-3 mr-1" /> {t.editor.splitCue}
                </Button>
                <Button variant="outline" size="sm" className="flex-1 h-8 text-xs" onClick={mergeWithNext}>
                  <Merge className="w-3 h-3 mr-1" /> {t.editor.mergeNext}
                </Button>
              </div>
            </div>
          )}
        </aside>
      </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
