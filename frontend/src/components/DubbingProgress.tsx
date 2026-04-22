import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import { CheckCircle, XCircle, Loader2, Download, Ban, PauseCircle, Play } from 'lucide-react';
import api from '../lib/api';
import { Button } from './ui/button';

interface JobStatusResponse {
  status: 'pending' | 'processing' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  message?: string | null;
  error?: string | null;
  output_path?: string | null;
}

interface DubbingProgressProps {
  jobId: string;
  onComplete?: (outputPath: string) => void;
  onError?: (error: string) => void;
}

export const DubbingProgress = ({ jobId, onComplete, onError }: DubbingProgressProps) => {
  const [data, setData] = useState<JobStatusResponse | null>(null);
  const intervalRef = useRef<number | null>(null);
  const pollCountRef = useRef(0);

  const poll = useCallback(async () => {
    try {
      const response = await api.get(`/status/${jobId}`);
      const job = response.data;
      setData(job);
      pollCountRef.current++;

      if (job.status === 'completed') {
        if (intervalRef.current) clearInterval(intervalRef.current);
        if (onComplete) onComplete(job.output_path);
        return;
      }
      if (job.status === 'failed') {
        if (intervalRef.current) clearInterval(intervalRef.current);
        if (onError) onError(job.error || 'Unknown error');
        return;
      }
      if (job.status === 'cancelled') {
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }
    } catch (error) {
      console.error('Polling error', error);
    }
  }, [jobId, onComplete, onError]);

  useEffect(() => {
    const getPollInterval = () => pollCountRef.current < 10 ? 1500 : 4000;

    const startPolling = () => {
      poll();
      intervalRef.current = window.setInterval(poll, getPollInterval());
    };

    startPolling();
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [jobId, poll]);

  const handleCancel = async () => {
    try {
      await api.post(`/jobs/${jobId}/cancel`);
      poll();
    } catch (error) {
      console.error('Failed to cancel job', error);
    }
  };

  const handlePause = async () => {
    try {
      await api.post(`/jobs/${jobId}/pause`);
      poll();
    } catch (error) {
      console.error('Failed to pause job', error);
    }
  };

  const handleResume = async () => {
    try {
      await api.post(`/jobs/${jobId}/resume`);
      // Restart polling
      if (intervalRef.current) clearInterval(intervalRef.current);
      pollCountRef.current = 0;
      const getPollInterval = () => pollCountRef.current < 10 ? 1500 : 4000;
      intervalRef.current = window.setInterval(poll, getPollInterval());
      poll();
    } catch (error) {
      console.error('Failed to resume job', error);
    }
  };

  if (!data) return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="animate-spin w-8 h-8 text-indigo-400" />
    </div>
  );

  const isCompleted = data.status === 'completed';
  const isFailed = data.status === 'failed';
  const isProcessing = data.status === 'processing';
  const isCancelled = data.status === 'cancelled';
  const isPaused = data.status === 'paused';
  const outputFilename = data.output_path?.split(/[\\/]/).pop();

  // Use real progress from backend
  const progressValue = data.progress ?? (isCompleted ? 100 : isProcessing ? 50 : isFailed || isCancelled ? 0 : 0);

  return (
    <Card className="w-full max-w-lg mx-auto mt-8 border border-slate-800 bg-slate-900/50 shadow-xl overflow-hidden">
      <CardHeader className="bg-slate-900/80 pb-4">
        <CardTitle className="flex items-center justify-between">
          <span className="text-lg font-bold flex items-center gap-2">
            {isCompleted ? <CheckCircle className="text-green-500" /> :
             isFailed ? <XCircle className="text-red-500" /> :
             isCancelled ? <Ban className="text-orange-500" /> :
             isPaused ? <PauseCircle className="text-yellow-500" /> :
             <Loader2 className="animate-spin text-indigo-400" />}
            {isCompleted ? 'Video Ready!' :
             isFailed ? 'Generation Failed' :
             isCancelled ? 'Job Cancelled' :
             isPaused ? 'Job Paused' :
             'Generating Video...'}
          </span>
          <Badge variant={
            isCompleted ? "default" :
            isFailed ? "destructive" :
            isCancelled ? "secondary" :
            "outline"
          }>
            {data.status.toUpperCase()}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6 space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm font-medium">
            <span>Progress</span>
            <span>
              {isCompleted ? '100%' :
               isCancelled ? 'Cancelled' :
               isFailed ? 'Failed' :
               `${progressValue}%`}
            </span>
          </div>
          <Progress value={progressValue} className="h-2" />
        </div>

        {/* Live status message */}
        <div className="text-sm text-slate-400 italic min-h-[1.5rem]">
          {isCompleted ? '✅ Video ready for download!' :
           isFailed ? `❌ ${data.error}` :
           isCancelled ? '🚫 Job was cancelled by user.' :
           isPaused ? '⏸️ Job is paused. Resume to continue.' :
           data.message ? `⏳ ${data.message}` :
           'Waiting in queue...'}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {isProcessing && (
            <>
              <Button variant="outline" className="flex-1 text-yellow-400 border-yellow-500/20 hover:bg-yellow-500/10" onClick={handlePause}>
                <PauseCircle className="w-4 h-4 mr-2" /> Pause
              </Button>
              <Button variant="outline" className="flex-1 text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={handleCancel}>
                <Ban className="w-4 h-4 mr-2" /> Cancel
              </Button>
            </>
          )}
          {isPaused && (
            <>
              <Button variant="outline" className="flex-1 text-green-400 border-green-500/20 hover:bg-green-500/10" onClick={handleResume}>
                <Play className="w-4 h-4 mr-2" /> Resume
              </Button>
              <Button variant="outline" className="flex-1 text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={handleCancel}>
                <Ban className="w-4 h-4 mr-2" /> Cancel
              </Button>
            </>
          )}
          {data.status === 'pending' && (
            <Button variant="outline" className="w-full text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={handleCancel}>
              <Ban className="w-4 h-4 mr-2" /> Cancel
            </Button>
          )}
        </div>

        {isCompleted && data.output_path && (
          <div className="space-y-3">
            {/* Video Preview */}
            <div className="rounded-lg overflow-hidden border border-slate-700 bg-black">
              <video
                controls
                className="w-full max-h-[300px]"
                src={outputFilename ? `http://localhost:8000/storage/output/${outputFilename}` : undefined}
              >
                Your browser does not support the video tag.
              </video>
            </div>
            <Button className="w-full bg-indigo-600 hover:bg-indigo-500" onClick={() => {
              const filename = outputFilename;
              if (!filename) {
                return;
              }
              const a = document.createElement('a');
              a.href = `http://localhost:8000/storage/output/${filename}`;
              a.download = filename || 'output.mp4';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
            }}>
              <Download className="w-4 h-4 mr-2" /> Download Result
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
