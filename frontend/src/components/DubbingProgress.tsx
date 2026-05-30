import { useState, useEffect, useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

import { Badge } from '../components/ui/badge';
import { CheckCircle, XCircle, Loader2, Download, Ban, PauseCircle, Play } from 'lucide-react';
import api from '../lib/api';
import { apiOrigin } from '../lib/api';
import { Button } from './ui/button';
import { VideoPlayer } from './VideoPlayer';
import { useJobEvents } from '../lib/jobEvents';
import { useI18n } from '@/i18n/I18nProvider';

interface ShortPart {
  index: number;
  label: string;
  filename: string;
  url: string;
  duration?: number;
}

interface JobStatusResponse {
  status: 'pending' | 'processing' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  message?: string | null;
  error?: string | null;
  output_path?: string | null;
  parts?: ShortPart[];
  pixverse_enabled?: boolean;
  pixverse_provider?: string | null;
  pixverse_fallback_used?: boolean;
}

interface DubbingProgressProps {
  jobId: string;
  onComplete?: (outputPath: string) => void;
  onError?: (error: string) => void;
}

export const DubbingProgress = ({ jobId, onComplete, onError }: DubbingProgressProps) => {
  const { t } = useI18n();
  const [data, setData] = useState<JobStatusResponse | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const intervalRef = useRef<number | null>(null);

  const loadJob = useCallback(async () => {
    try {
      const response = await api.get(`/status/${jobId}`);
      const job = response.data;
      setData(job);
    } catch (error) {
      console.error('Job load error', error);
    }
  }, [jobId]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadJob();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [jobId, loadJob]);

  useEffect(() => {
    if (sseConnected) {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }
    intervalRef.current = window.setInterval(() => {
      void loadJob();
    }, 20000);
    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId, loadJob, sseConnected]);

  useJobEvents<JobStatusResponse>(
    (payload) => {
      if (payload.job_id !== jobId) {
        return;
      }
      setData(payload.job);
    },
    { onConnectionChange: setSseConnected },
  );

  useEffect(() => {
    if (!data) return;
    if (data.status === 'completed' && data.output_path) {
      onComplete?.(data.output_path);
    }
    if (data.status === 'failed') {
      onError?.(data.error || 'Unknown error');
    }
  }, [data, onComplete, onError]);

  const handleCancel = async () => {
    try {
      await api.post(`/jobs/${jobId}/cancel`);
      void loadJob();
    } catch (error) {
      console.error('Failed to cancel job', error);
    }
  };

  const handlePause = async () => {
    try {
      await api.post(`/jobs/${jobId}/pause`);
      void loadJob();
    } catch (error) {
      console.error('Failed to pause job', error);
    }
  };

  const handleResume = async () => {
    try {
      await api.post(`/jobs/${jobId}/resume`);
      void loadJob();
    } catch (error) {
      console.error('Failed to resume job', error);
    }
  };

  if (!data) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center py-20">
      <Loader2 className="animate-spin w-8 h-8 text-indigo-400" />
    </motion.div>
  );

  const isCompleted = data.status === 'completed';
  const isFailed = data.status === 'failed';
  const isProcessing = data.status === 'processing';
  const isCancelled = data.status === 'cancelled';
  const isPaused = data.status === 'paused';
  const outputFilename = data.output_path?.split(/[\\/]/).pop();
  const pixverseEnabled = Boolean(data.pixverse_enabled);
  const pixverseProvider =
    data.pixverse_provider === 'pixverse'
      ? t.progress.pixverseProvider
      : data.pixverse_provider === 'pixverse_cli'
        ? t.progress.pixverseCliProvider
      : data.pixverse_provider === 'pixverse_external'
        ? t.progress.pixverseExternalProvider
      : data.pixverse_provider === 'local_fallback'
        ? t.progress.localFallbackProvider
        : data.pixverse_provider === 'pending'
          ? t.progress.pixversePending
          : null;

  // Use real progress from backend
  const progressValue = data.progress ?? (isCompleted ? 100 : isProcessing ? 50 : isFailed || isCancelled ? 0 : 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="relative group w-full max-w-lg mx-auto mt-8"
    >
      <div className="pointer-events-none absolute -inset-0.5 bg-gradient-to-b from-indigo-500/20 to-purple-500/20 rounded-2xl blur opacity-100 transition duration-500" />
      <Card className="relative z-10 border border-white/10 bg-slate-900/80 backdrop-blur-xl shadow-2xl overflow-visible rounded-2xl">
        <CardHeader className="bg-white/5 pb-4 border-b border-white/5">
          <CardTitle className="flex items-center justify-between">
            <span className="text-lg font-bold flex items-center gap-3">
              {isCompleted ? <div className="p-1.5 bg-green-500/20 rounded-lg"><CheckCircle className="text-green-400 w-5 h-5" /></div> :
               isFailed ? <div className="p-1.5 bg-red-500/20 rounded-lg"><XCircle className="text-red-400 w-5 h-5" /></div> :
               isCancelled ? <div className="p-1.5 bg-orange-500/20 rounded-lg"><Ban className="text-orange-400 w-5 h-5" /></div> :
               isPaused ? <div className="p-1.5 bg-yellow-500/20 rounded-lg"><PauseCircle className="text-yellow-400 w-5 h-5" /></div> :
               <div className="p-1.5 bg-indigo-500/20 rounded-lg"><Loader2 className="animate-spin text-indigo-400 w-5 h-5" /></div>}
              {isCompleted ? t.progress.completed :
               isFailed ? t.progress.failed :
               isCancelled ? t.progress.cancelled :
               isPaused ? t.progress.paused :
               t.progress.processing}
            </span>
            <Badge variant={
              isCompleted ? "default" :
              isFailed ? "destructive" :
              isCancelled ? "secondary" :
              "outline"
            } className={isCompleted ? "bg-green-500 hover:bg-green-600" : isFailed ? "bg-red-500" : isCancelled ? "bg-orange-500" : "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"}>
              {data.status.toUpperCase()}
            </Badge>
          </CardTitle>
          {(pixverseEnabled || pixverseProvider) && (
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge className="bg-violet-500/15 text-violet-200 border-violet-500/30">
                {t.progress.pixverseEnabled}
              </Badge>
              {pixverseProvider && (
                <Badge className="bg-cyan-500/15 text-cyan-200 border-cyan-500/30">
                  {pixverseProvider}
                </Badge>
              )}
              {data.pixverse_fallback_used && (
                <Badge className="bg-amber-500/15 text-amber-200 border-amber-500/30">
                  {t.progress.localFallbackActive}
                </Badge>
              )}
            </div>
          )}
        </CardHeader>
        <CardContent className="pt-6 space-y-6">
          <div className="space-y-3">
            <div className="flex justify-between text-xs font-bold uppercase tracking-widest text-slate-400">
              <span>{t.progress.progressLabel}</span>
              <span className="text-indigo-400">
                {isCompleted ? '100%' :
                 isCancelled ? t.progress.cancelledLabel :
                 isFailed ? t.progress.failedLabel :
                 `${Number(progressValue).toFixed(progressValue % 1 === 0 ? 0 : 1)}%`}
              </span>
            </div>
            <div className="relative h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <motion.div
                className={`absolute left-0 top-0 bottom-0 ${isCompleted ? 'bg-green-500' : isFailed ? 'bg-red-500' : isCancelled ? 'bg-orange-500' : 'bg-gradient-to-r from-indigo-500 to-purple-500'}`}
                animate={{ width: `${progressValue}%` }}
                transition={{ type: 'spring', stiffness: 120, damping: 22 }}
              >
                {!isCompleted && !isFailed && !isCancelled && (
                   <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_2s_infinite]"></div>
                )}
              </motion.div>
            </div>
          </div>

        {/* Live status message */}
        <AnimatePresence mode="wait">
          <motion.div
            key={`${data.status}-${data.message || data.error || 'idle'}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="text-sm text-slate-400 italic min-h-[1.5rem]"
          >
            {isCompleted ? `✅ ${t.progress.readyMessage}` :
             isFailed ? `❌ ${data.error}` :
             isCancelled ? `🚫 ${t.progress.cancelledMessage}` :
             isPaused ? `⏸️ ${t.progress.pausedMessage}` :
             data.message ? `⏳ ${data.message}` :
             t.progress.pending}
          </motion.div>
        </AnimatePresence>

        {/* Action buttons */}
        <div className="flex gap-2">
          {isProcessing && (
            <>
              <Button variant="outline" className="flex-1 text-yellow-400 border-yellow-500/20 hover:bg-yellow-500/10" onClick={handlePause}>
                <PauseCircle className="w-4 h-4 mr-2" /> {t.progress.pause}
              </Button>
              <Button variant="outline" className="flex-1 text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={handleCancel}>
                <Ban className="w-4 h-4 mr-2" /> {t.progress.cancel}
              </Button>
            </>
          )}
          {isPaused && (
            <>
              <Button variant="outline" className="flex-1 text-green-400 border-green-500/20 hover:bg-green-500/10" onClick={handleResume}>
                <Play className="w-4 h-4 mr-2" /> {t.progress.resume}
              </Button>
              <Button variant="outline" className="flex-1 text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={handleCancel}>
                <Ban className="w-4 h-4 mr-2" /> {t.progress.cancel}
              </Button>
            </>
          )}
          {data.status === 'pending' && (
            <Button variant="outline" className="w-full text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={handleCancel}>
              <Ban className="w-4 h-4 mr-2" /> Cancel
            </Button>
          )}
        </div>

        {isCompleted && data.parts && data.parts.length > 0 && (
          <div className="space-y-4 pt-4 border-t border-white/5">
            <p className="text-sm font-semibold text-emerald-300">{t.shorts.allPartsReady}</p>
            {data.parts.map((part) => (
              <div key={part.index} className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">{part.label}</span>
                  {part.duration != null && (
                    <span className="text-xs text-slate-500">{part.duration.toFixed(1)}s</span>
                  )}
                </div>
                <VideoPlayer
                  src={`${apiOrigin}${part.url}`}
                  maxHeightClass="max-h-64"
                />
                <Button
                  variant="outline"
                  className="w-full border-emerald-500/30 text-emerald-300"
                  onClick={() => {
                    const a = document.createElement('a');
                    a.href = `${apiOrigin}${part.url}`;
                    a.download = part.filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                  }}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {t.shorts.downloadPart} {part.label}
                </Button>
              </div>
            ))}
          </div>
        )}

        {isCompleted && data.output_path && (!data.parts || data.parts.length === 0) && (
          <div className="space-y-4 pt-4 border-t border-white/5">
            {outputFilename && (
              <VideoPlayer
                key={outputFilename}
                src={`${apiOrigin}/storage/output/${outputFilename}`}
              />
            )}
            <Button className="w-full btn-glow bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-6 rounded-xl text-base shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_25px_rgba(79,70,229,0.5)] transition-all transform hover:-translate-y-0.5" onClick={() => {
              const filename = outputFilename;
              if (!filename) {
                return;
              }
              const a = document.createElement('a');
              a.href = `${apiOrigin}/storage/output/${filename}`;
              a.download = filename || 'output.mp4';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
            }}>
              <Download className="w-5 h-5 mr-2" /> {t.progress.download}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
    </motion.div>
  );
};
