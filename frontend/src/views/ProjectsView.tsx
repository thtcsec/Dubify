import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Play, Download, Clock, Loader2, Ban, PauseCircle, XCircle, RefreshCw } from 'lucide-react';
import api from '../lib/api';
import { useJobEvents } from '../lib/jobEvents';
import { useI18n } from '@/i18n/I18nProvider';
import { DeleteAllJobsButton } from '@/components/jobs/DeleteAllJobsButton';
import { JobEditableName } from '@/components/jobs/JobEditableName';

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
  const { t } = useI18n();
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

  useJobEvents<Job>((payload) => {
    const nextJob = payload.job;
    setProjects((currentProjects) => {
      const existingIndex = currentProjects.findIndex((job) => job.id === nextJob.id);
      if (existingIndex >= 0) {
        const updated = [...currentProjects];
        updated[existingIndex] = nextJob;
        return updated;
      }
      return [nextJob, ...currentProjects];
    });
  });

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
        <p>{t.projects.loading}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">
            <span className="bg-gradient-to-br from-indigo-500 to-purple-500 text-transparent bg-clip-text">
              {t.projects.title}
            </span>
          </h1>
          <p className="text-slate-400">{t.projects.subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <DeleteAllJobsButton scope="completed" variant="projects" onDeleted={fetchProjects} />
          <Button variant="ghost" size="icon" onClick={fetchProjects} title={t.projects.refresh}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {projects.length === 0 ? (
          <Card className="col-span-full bg-white/5 border-white/10 border-dashed p-20 text-center">
            <p className="text-slate-500">{t.projects.empty}</p>
          </Card>
        ) : (
          projects.map((project) => (
            <div key={project.id} className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
              <Card className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden rounded-2xl flex flex-col h-full">
                <div className="aspect-video bg-black flex items-center justify-center relative overflow-hidden group/video cursor-pointer border-b border-white/5">
                  <Play className="w-12 h-12 text-white/20 group-hover/video:text-indigo-400 group-hover/video:scale-110 transition-all duration-300" />
                  <div className="absolute top-3 right-3">
                    <Badge className={`${statusBadgeClass(project.status)} shadow-lg backdrop-blur-md`}>
                      {project.status.toUpperCase()}
                    </Badge>
                  </div>
                  {project.type && (
                    <div className="absolute top-3 left-3">
                      <Badge variant="outline" className="text-[10px] bg-black/60 backdrop-blur-md border-white/10 text-white">
                        {project.type}
                      </Badge>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover/video:opacity-100 transition-opacity duration-300"></div>
                </div>
                <CardHeader className="p-5 flex-1">
                  <CardTitle className="text-lg font-bold group-hover:text-indigo-400 transition-colors">
                    <JobEditableName
                      jobId={project.id}
                      filename={project.filename || 'Untitled Project'}
                      onRenamed={(name) =>
                        setProjects((list) =>
                          list.map((p) => (p.id === project.id ? { ...p, filename: name } : p)),
                        )
                      }
                    />
                  </CardTitle>
                  <CardDescription className="flex items-center gap-2 text-xs mt-1">
                    <Clock className="w-3.5 h-3.5 text-indigo-400" /> 
                    <span className="font-semibold text-slate-300">{project.target_lang ? `Target: ${project.target_lang}` : 'dubbing'}</span>
                    {project.message && (
                      <>
                        <span className="text-slate-600 px-1">•</span>
                        <span className="text-slate-400 truncate">{project.message}</span>
                      </>
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
            </div>
          ))
        )}
      </div>
    </div>
  );
}
