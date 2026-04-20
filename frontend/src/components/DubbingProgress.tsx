import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, Clock, Loader2, Download } from 'lucide-react';
import api from '@/lib/api';
import { Button } from './ui/button';

interface DubbingProgressProps {
  jobId: string;
  onComplete?: (outputPath: string) => void;
  onError?: (error: string) => void;
}

export const DubbingProgress = ({ jobId, onComplete, onError }: DubbingProgressProps) => {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/status/${jobId}`);
        const job = response.data;
        setData(job);

        if (job.status === 'completed') {
          clearInterval(interval);
          if (onComplete) onComplete(job.output_path);
        } else if (job.status === 'failed') {
          clearInterval(interval);
          if (onError) onError(job.error || 'Unknown error');
        }
      } catch (err) {
        console.error('Polling error', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  if (!data) return <Loader2 className="animate-spin" />;

  const isCompleted = data.status === 'completed';
  const isFailed = data.status === 'failed';

  return (
    <Card className="w-full max-w-md mx-auto mt-8 border-2 border-primary/20 shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4">
      <CardHeader className="bg-primary/5 pb-4">
        <CardTitle className="flex items-center justify-between">
          <span className="text-lg font-bold flex items-center gap-2">
            {isCompleted ? <CheckCircle className="text-green-500" /> : 
             isFailed ? <XCircle className="text-red-500" /> : 
             <Loader2 className="animate-spin text-primary" />}
            Dubbing Job
          </span>
          <Badge variant={isCompleted ? "default" : isFailed ? "destructive" : "outline"}>
            {data.status.toUpperCase()}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6 space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm font-medium">
            <span>Progress</span>
            <span>{isCompleted ? '100%' : data.status === 'processing' ? 'Processing...' : 'Pending'}</span>
          </div>
          <Progress value={isCompleted ? 100 : data.status === 'processing' ? 66 : 10} className="h-2" />
        </div>
        
        <div className="text-sm text-muted-foreground italic">
          {isCompleted ? 'Video ready for download!' : 
           isFailed ? `Error: ${data.error}` : 
           'Please wait while we dub your video...'}
        </div>

        {isCompleted && (
           <Button className="w-full mt-4" onClick={() => {
              const filename = data.output_path.split(/[\\/]/).pop();
              window.open(`http://localhost:8000/storage/output/${filename}`);
           }}>
              <Download className="w-4 h-4 mr-2" /> Download Result
           </Button>
        )}
      </CardContent>
    </Card>
  );
};
