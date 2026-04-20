import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { AppSidebar } from './components/AppSidebar';
import { DashboardHeader } from './components/dashboard/Header';

// Views
import { DashboardView } from './views/DashboardView';
import { ProjectsView } from './views/ProjectsView';
import { HistoryView, SettingsView } from './views/ActivityViews';
import { HelpView } from './views/HelpView';

import api from './lib/api';

export default function App() {
  // Global State
  const [currentView, setCurrentView] = useState('dashboard');
  const [targetLang, setTargetLang] = useState('vi');
  const [jobId, setJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Dashboard Input States
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

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <DashboardView 
            targetLang={targetLang}
            setTargetLang={setTargetLang}
            jobId={jobId}
            setJobId={setJobId}
            isLoading={isLoading}
            file={file}
            setFile={setFile}
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            videoInfo={videoInfo}
            handleFetchInfo={handleFetchInfo}
            handleStartDubbing={handleStartDubbing}
            resetProject={resetProject}
          />
        );
      case 'projects':
        return <ProjectsView />;
      case 'history':
        return <HistoryView />;
      case 'settings':
        return <SettingsView />;
      case 'help':
        return <HelpView />;
      default:
        return <div>View not found</div>;
    }
  };

  return (
    <SidebarProvider defaultOpen>
      <AppSidebar currentView={currentView} onViewChange={setCurrentView} />
      <SidebarInset className="bg-slate-950 flex-1 min-w-0 transition-all duration-200 ease-linear overflow-hidden">
        <DashboardHeader currentView={currentView} />

        <div className="p-8 w-full min-h-[calc(100vh-4rem)]">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentView}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
            >
              {renderView()}
            </motion.div>
          </AnimatePresence>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
