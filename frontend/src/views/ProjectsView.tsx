import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Play, Download, Clock, Loader2, Ban, PauseCircle, XCircle, RefreshCw } from 'lucide-react';
import api from '../lib/api';

interface Job {
  id: string;
  filename: string;
  type: string;
  status: string;
  message: string | null;
  error: string | null;
  output_path: string | null;
  created_at: string;
  target_lang?: string;
}

function statusBadgeClass(status: string) {
  switch (status) {
    case 'completed': return 'bg-green-500/20 text-green-400';
    case 'failed': return 'bg-red-500/20 text-red-400';
    case 'processing': return 'bg-blue-500/20 text-blue-400';
    case 'cancelled': return 'bg-orange-500/20 text-orange-400';
    case 'paused': return 'bg-yellow-500/20 text-yellow-400';
    default: return 'bg-slate-500/20 text-slate-400';
  }
}

export function ProjectsView() {
  const [projects, setProjects] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/jobs', { params: { limit: 50 } });
      setProjects(response.data.jobs || []);
    } catch (error) {
      console.error('Failed to fetch projects', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void fetchProjects();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  const handleCancel = async (jobId: string) => {
    try {
      await api.post(`/jobs/${jobId}/cancel`);
      fetchProjects();
    } catch (error) {
      console.error('Failed to cancel job', error);
    }
  };

  const handlePause = async (jobId: string) => {
    try {
      await api.post(`/jobs/${jobId}/pause`);
      fetchProjects();
    } catch (error) {
      console.error('Failed to pause job', error);
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await api.post(`/jobs/${jobId}/resume`);
      fetchProjects();
    } catch (error) {
      console.error('Failed to resume job', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin mb-4" />
        <p>Loading projects...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">My Projects</h1>
          <p className="text-slate-400">Manage and download your AI dubbed videos.</p>
        </div>
        <Button variant="ghost" size="icon" onClick={fetchProjects} title="Refresh">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {projects.length === 0 ? (
          <Card className="col-span-full bg-white/5 border-white/10 border-dashed p-20 text-center">
            <p className="text-slate-500">No projects found. Create your first one in the Dashboard!</p>
          </Card>
        ) : (
          projects.map((project) => (
            <Card key={project.id} className="bg-white/5 border-white/10 overflow-hidden hover:border-white/20 transition-all group">
              <div className="aspect-video bg-slate-900 flex items-center justify-center relative">
                <Play className="w-12 h-12 text-white/20 group-hover:text-primary/50 transition-colors" />
                <div className="absolute top-2 right-2">
                  <Badge className={statusBadgeClass(project.status)}>
                    {project.status.toUpperCase()}
                  </Badge>
                </div>
                {project.type && (
                  <div className="absolute top-2 left-2">
                    <Badge variant="outline" className="text-[10px] bg-black/40 backdrop-blur-sm">
                      {project.type}
                    </Badge>
                  </div>
                )}
              </div>
              <CardHeader className="p-4">
                <CardTitle className="text-base truncate">{project.filename || 'Untitled Project'}</CardTitle>
                <CardDescription className="flex items-center gap-2 text-xs">
                  <Clock className="w-3 h-3" /> {project.target_lang ? `Target: ${project.target_lang}` : 'dubbing'}
                  {project.message && (
                    <span className="text-slate-500 truncate">· {project.message}</span>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 pt-0 flex gap-2">
                {project.status === 'completed' && project.output_path && (
                  <>
                    <Button size="sm" variant="secondary" className="flex-1" onClick={() => {
                      const filename = project.output_path!.split(/[\\/]/).pop();
                      window.open(`http://localhost:8000/storage/output/${filename}`);
                    }}>
                      <Play className="w-4 h-4 mr-2" /> Play
                    </Button>
                    <Button size="sm" variant="outline" className="flex-1" onClick={() => {
                      const filename = project.output_path!.split(/[\\/]/).pop();
                      const a = document.createElement('a');
                      a.href = `http://localhost:8000/storage/output/${filename}`;
                      a.download = filename || 'output.mp4';
                      a.click();
                    }}>
                      <Download className="w-4 h-4 mr-2" /> Download
                    </Button>
                  </>
                )}
                {(project.status === 'processing' || project.status === 'pending') && (
                  <>
                    {project.status === 'processing' && (
                      <Button size="sm" variant="outline" className="flex-1 text-yellow-400 border-yellow-500/20 hover:bg-yellow-500/10" onClick={() => handlePause(project.id)}>
                        <PauseCircle className="w-4 h-4 mr-2" /> Pause
                      </Button>
                    )}
                    <Button size="sm" variant="outline" className="flex-1 text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={() => handleCancel(project.id)}>
                      <Ban className="w-4 h-4 mr-2" /> Cancel
                    </Button>
                  </>
                )}
                {project.status === 'paused' && (
                  <>
                    <Button size="sm" variant="outline" className="flex-1 text-green-400 border-green-500/20 hover:bg-green-500/10" onClick={() => handleResume(project.id)}>
                      <Play className="w-4 h-4 mr-2" /> Resume
                    </Button>
                    <Button size="sm" variant="outline" className="flex-1 text-red-400 border-red-500/20 hover:bg-red-500/10" onClick={() => handleCancel(project.id)}>
                      <Ban className="w-4 h-4 mr-2" /> Cancel
                    </Button>
                  </>
                )}
                {project.status === 'failed' && project.error && (
                  <div className="flex items-center gap-2 text-xs text-red-400 w-full">
                    <XCircle className="w-4 h-4 shrink-0" />
                    <span className="truncate">{project.error}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
