import { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import api, { apiOrigin } from '../lib/api';
import { useJobEvents } from '../lib/jobEvents';

interface Job {
  id: string;
  filename: string;
  type: string;
  status: string;
  output_path: string | null;
  created_at: string;
  message?: string | null;
}

interface JobArtifacts {
  subtitle_path: string | null;
  transcript_path: string | null;
  session_dir: string | null;
}

interface Cue {
  start: string;
  end: string;
  text: string;
}

function parseSubtitleText(raw: string): Cue[] {
  const blocks = raw.split(/\r?\n\r?\n/).map((block) => block.trim()).filter(Boolean);
  const cues: Cue[] = [];

  for (const block of blocks) {
    const lines = block.split(/\r?\n/).filter(Boolean);
    const timeLineIndex = lines.findIndex((line) => line.includes('-->'));
    if (timeLineIndex === -1) continue;
    const [start, end] = lines[timeLineIndex].split('-->').map((item) => item.trim());
    const text = lines.slice(timeLineIndex + 1).join(' ').trim();
    if (text) {
      cues.push({ start, end, text });
    }
  }

  return cues;
}

export function StudioEditorView() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [subtitleText, setSubtitleText] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchCompletedJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/jobs', { params: { limit: 100, status: 'completed' } });
      const completedJobs = (response.data.jobs || []).filter((job: Job) => job.output_path);
      setJobs(completedJobs);
      setSelectedJobId((current) => current || completedJobs[0]?.id || null);
    } catch (error) {
      console.error('Failed to fetch completed jobs for studio editor', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void fetchCompletedJobs();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [fetchCompletedJobs]);

  useJobEvents<Job>((payload) => {
    const nextJob = payload.job;
    if (nextJob.status !== 'completed' || !nextJob.output_path) {
      return;
    }
    setJobs((currentJobs) => {
      const existingIndex = currentJobs.findIndex((job) => job.id === nextJob.id);
      if (existingIndex >= 0) {
        const updated = [...currentJobs];
        updated[existingIndex] = nextJob;
        return updated;
      }
      return [nextJob, ...currentJobs];
    });
    setSelectedJobId((current) => current || nextJob.id);
  });

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) || null,
    [jobs, selectedJobId],
  );

  useEffect(() => {
    const loadArtifacts = async () => {
      if (!selectedJobId) {
        setSubtitleText('');
        return;
      }

      try {
        const response = await api.get<JobArtifacts>(`/jobs/${selectedJobId}/artifacts`);
        const subtitlePath = response.data.subtitle_path;
        if (!subtitlePath) {
          setSubtitleText('');
          return;
        }

        const normalized = subtitlePath.replace(/\\/g, '/');
        const storageIndex = normalized.indexOf('/storage/');
        const tempIndex = normalized.indexOf('/temp/');
        let assetUrl: string | null = null;

        if (storageIndex >= 0) {
          assetUrl = `${apiOrigin}${normalized.slice(storageIndex)}`;
        } else if (tempIndex >= 0) {
          assetUrl = `${apiOrigin}/storage${normalized.slice(tempIndex)}`;
        }

        if (!assetUrl) {
          setSubtitleText('');
          return;
        }

        const subtitleResponse = await fetch(assetUrl);
        setSubtitleText(await subtitleResponse.text());
      } catch (error) {
        console.error('Failed to load editor artifacts', error);
        setSubtitleText('');
      }
    };

    void loadArtifacts();
  }, [selectedJobId]);

  const subtitleCues = useMemo(() => parseSubtitleText(subtitleText), [subtitleText]);
  const videoUrl = selectedJob?.output_path
    ? `${apiOrigin}/storage/output/${selectedJob.output_path.split(/[\\/]/).pop()}`
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Studio Editor</h1>
        <p className="text-slate-400">Open completed videos, inspect subtitles, and prepare the next editing pass.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[280px_minmax(0,1fr)_340px] gap-6">
        <Card className="bg-white/5 border-white/10">
          <CardHeader>
            <CardTitle className="text-lg">Completed Videos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[72vh] overflow-y-auto">
            {isLoading ? (
              <p className="text-sm text-slate-400">Loading completed jobs...</p>
            ) : jobs.length === 0 ? (
              <p className="text-sm text-slate-500">No completed videos yet.</p>
            ) : (
              jobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => setSelectedJobId(job.id)}
                  className={`w-full rounded-xl border p-3 text-left transition-colors ${
                    selectedJobId === job.id
                      ? 'border-indigo-400/50 bg-indigo-500/10'
                      : 'border-white/10 bg-black/20 hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium truncate">{job.filename || 'Untitled'}</p>
                    <Badge variant="outline" className="text-[10px]">
                      {job.type}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-400 truncate">{job.message || 'Completed render'}</p>
                  <p className="mt-2 text-[10px] text-slate-500">{new Date(job.created_at).toLocaleString()}</p>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-white/5 border-white/10">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Preview</CardTitle>
              {videoUrl && (
                <Button variant="outline" size="sm" onClick={() => window.open(videoUrl, '_blank')}>
                  Open Source Video
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {videoUrl ? (
                <div className="rounded-2xl overflow-hidden border border-white/10 bg-black">
                  <video controls className="w-full max-h-[68vh]" src={videoUrl} />
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-white/10 p-16 text-center text-slate-500">
                  Select a completed job to open it in Studio.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <CardTitle className="text-lg">Timeline Sketch</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {subtitleCues.length === 0 ? (
                <p className="text-sm text-slate-500">No subtitle track found for this job yet.</p>
              ) : (
                subtitleCues.slice(0, 12).map((cue, index) => (
                  <div key={`${cue.start}-${index}`} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{cue.start}</span>
                      <span>{cue.end}</span>
                    </div>
                    <div className="rounded-full bg-slate-800 h-3 overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" style={{ width: `${Math.min(100, 18 + cue.text.length * 1.2)}%` }} />
                    </div>
                    <p className="text-xs text-slate-300 truncate">{cue.text}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="bg-white/5 border-white/10">
          <CardHeader>
            <CardTitle className="text-lg">Subtitle Workspace</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-400">
              This is the first pass of the editor tab. It lets us open completed renders and inspect subtitle assets before wiring full CapCut-style edits.
            </p>
            <textarea
              value={subtitleText}
              onChange={(event) => setSubtitleText(event.target.value)}
              className="min-h-[420px] w-full rounded-xl border border-white/10 bg-black/30 p-4 text-sm text-slate-200 outline-none"
              placeholder="Subtitle track will appear here when available."
            />
            <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/10 p-3 text-xs text-yellow-100">
              Subtitle editing UI is live here, but saving a new render pass is the next wiring step.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
