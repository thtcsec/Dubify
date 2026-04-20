import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Play, Download, Trash2, Clock, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import api from '@/lib/api';

export function ProjectsView() {
  const [projects, setProjects] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await api.get('/projects');
        // Convert map to array and sort by latest
        const projectList = Object.entries(response.data).map(([id, data]: [string, any]) => ({
          id,
          ...data
        })).reverse();
        setProjects(projectList);
      } catch (err) {
        console.error('Failed to fetch projects');
      } finally {
        setIsLoading(false);
      }
    };
    fetchProjects();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin mb-4" />
        <p>Loading your projects...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">My Projects</h1>
        <p className="text-slate-400">Manage and download your AI dubbed videos.</p>
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
                    <Badge className={
                      project.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                      project.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                      'bg-blue-500/20 text-blue-400'
                    }>
                      {project.status.toUpperCase()}
                    </Badge>
                 </div>
              </div>
              <CardHeader className="p-4">
                <CardTitle className="text-base truncate">{project.filename || project.url || 'Untitled Project'}</CardTitle>
                <CardDescription className="flex items-center gap-2 text-xs">
                   <Clock className="w-3 h-3" /> Produced to: {project.target_lang || 'vi'}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 pt-0 flex gap-2">
                <Button size="sm" variant="secondary" className="flex-1" disabled={project.status !== 'completed'}>
                  <Play className="w-4 h-4 mr-2" /> Play
                </Button>
                <Button size="sm" variant="outline" className="flex-1" disabled={project.status !== 'completed'}>
                  <Download className="w-4 h-4 mr-2" /> Download
                </Button>
                <Button size="sm" variant="ghost" className="text-red-400/50 hover:text-red-400 hover:bg-red-400/10">
                   <Trash2 className="w-4 h-4" />
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
