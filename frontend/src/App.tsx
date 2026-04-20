import { useState } from 'react';
import { DubbingProgress } from './components/DubbingProgress';
import { Button } from './components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { AppSidebar } from './components/AppSidebar';
import { DashboardHeader } from './components/dashboard/Header';
import { VideoSourceSection } from './components/dashboard/VideoSourceSection';
import { ProjectSettings } from './components/dashboard/ProjectSettings';
import api from './lib/api';

export default function App() {
  // Global Orchestration State
  const [targetLang, setTargetLang] = useState('vi');
  const [jobId, setJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Input States
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<any>(null);

  const handleFetchInfo = async () => {
    if (!videoUrl) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append('url', videoUrl);
    try {
      const response = await api.post('/fetch-info', formData);
      setVideoInfo(response.data);
    } catch (err) {
      alert('Failed to fetch info. Ensure the URL is public.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartDubbing = async () => {
    setIsLoading(true);
    const formData = new FormData();
    formData.append('target_lang', targetLang);
    
    try {
      let response;
      if (file) {
        formData.append('file', file);
        response = await api.post('/dub', formData);
      } else {
        formData.append('url', videoUrl);
        response = await api.post('/dub-url', formData);
      }
      setJobId(response.data.job_id);
    } catch (err) {
      alert('Failed to start dubbing project.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetProject = () => {
    setJobId(null);
    setFile(null);
    setVideoUrl('');
    setVideoInfo(null);
  };

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="bg-slate-950">
        <DashboardHeader />

        <div className="p-8 max-w-6xl mx-auto w-full min-h-[calc(100vh-4rem)]">
          {!jobId && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
               <h1 className="text-3xl font-bold mb-2">Create New Dubbing Project</h1>
               <p className="text-slate-400 mb-8">Select a source to begin the AI localization process.</p>
            </motion.div>
          )}

          <main>
            <AnimatePresence mode="wait">
              {!jobId ? (
                <motion.div key="creation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Source Selection (Left) */}
                    <div className="lg:col-span-8">
                      <VideoSourceSection 
                        file={file} 
                        setFile={setFile}
                        videoUrl={videoUrl}
                        setVideoUrl={setVideoUrl}
                        videoInfo={videoInfo}
                        isLoading={isLoading}
                        onFetchInfo={handleFetchInfo}
                      />
                    </div>

                    {/* Settings & Action (Right) */}
                    <div className="lg:col-span-4">
                      <ProjectSettings 
                        targetLang={targetLang}
                        setTargetLang={setTargetLang}
                        isLoading={isLoading}
                        canStart={!!file || !!videoInfo}
                        onStart={handleStartDubbing}
                      />
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div key="progress" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
                   <div className="flex items-center justify-between mb-8">
                      <Button variant="ghost" className="text-slate-400" onClick={resetProject}>
                        ← Create New Project
                      </Button>
                      <div className="text-sm text-slate-500">Job ID: <span className="text-slate-300 font-mono">{jobId}</span></div>
                   </div>
                   <DubbingProgress 
                    jobId={jobId} 
                    onComplete={() => console.log('Job completed!')}
                    onError={(err) => alert(err)}
                   />
                </motion.div>
              )}
            </AnimatePresence>
          </main>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
