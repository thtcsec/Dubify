import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AppSidebar } from './components/AppSidebar';
import { DashboardHeader } from './components/dashboard/Header';
import { ErrorBoundary } from './components/ErrorBoundary';
import { isTimeoutError, extractApiErrorMessage } from './lib/errors';

// Views
import { DashboardView } from './views/DashboardView';
import { StudioView } from './views/StudioView';
import { StudioEditorView } from './views/StudioEditorView';
import { ShortsView } from './views/ShortsView';
import { ProjectsView } from './views/ProjectsView';
import { HistoryView, SettingsView } from './views/ActivityViews';
import { HelpView } from './views/HelpView';

import api, { uploadApi } from './lib/api';
import { useI18n } from './i18n/I18nProvider';

interface VideoInfo {
  title: string;
  duration: number;
  thumbnail?: string | null;
  source?: string | null;
  url?: string;
}

export default function App() {
  const { t } = useI18n();
  // Navigation State
  const [currentView, setCurrentView] = useState('dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Global State
  const [targetLang, setTargetLang] = useState('vi');
  const [jobId, setJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Dashboard Input States
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const handleFetchInfo = async () => {
    if (!videoUrl) return;
    setIsLoading(true);
    setFetchError(null);
    const formData = new FormData();
    formData.append('url', videoUrl);
    try {
      const response = await api.post('/fetch-info', formData);
      setVideoInfo(response.data);
    } catch (err) {
      if (isTimeoutError(err)) {
        setFetchError(t.dashboard.fetchTimeout);
      } else {
        setFetchError(extractApiErrorMessage(err, t.dashboard.fetchInvalid));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartDubbing = async () => {
    setIsLoading(true);
    setFetchError(null);
    const formData = new FormData();
    formData.append('target_lang', targetLang);
    try {
      let response;
      if (file) {
        formData.append('file', file);
        response = await uploadApi.post('/dub', formData);
      } else {
        formData.append('url', videoUrl);
        response = await api.post('/dub-url', formData);
      }
      setJobId(response.data.job_id);
    } catch (err) {
      if (isTimeoutError(err)) {
         setFetchError(t.dashboard.dubTimeoutHint);
      } else {
         setFetchError(extractApiErrorMessage(err, t.dashboard.dubFailed));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const resetProject = () => {
    setJobId(null);
    setFile(null);
    setVideoUrl('');
    setVideoInfo(null);
    setFetchError(null);
  };

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <DashboardView 
            targetLang={targetLang}
            setTargetLang={setTargetLang}
            jobId={jobId}
            isLoading={isLoading}
            file={file}
            setFile={setFile}
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            videoInfo={videoInfo}
            fetchError={fetchError}
            handleFetchInfo={handleFetchInfo}
            handleStartDubbing={handleStartDubbing}
            resetProject={resetProject}
          />
        );
      case 'studio':
        return (
          <StudioView
            targetLang={targetLang}
            setTargetLang={setTargetLang}
          />
        );
      case 'shorts':
        return (
          <ShortsView
            targetLang={targetLang}
            setTargetLang={setTargetLang}
          />
        );
      case 'editor':
        return <StudioEditorView />;
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
    <ErrorBoundary>
      <div className="flex h-screen w-full bg-slate-950 overflow-hidden text-white">
        <AppSidebar 
          currentView={currentView} 
          onViewChange={setCurrentView} 
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
        
        <div className="flex-1 min-w-0 flex flex-col h-full bg-slate-950">
          <DashboardHeader currentView={currentView} />

          <main className="flex-1 min-w-0 overflow-y-auto p-6 md:p-8">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentView}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.02 }}
                transition={{ duration: 0.2 }}
                className="max-w-7xl mx-auto h-full"
              >
                <ErrorBoundary>
                  {renderView()}
                </ErrorBoundary>
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
