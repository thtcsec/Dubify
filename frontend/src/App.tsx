import { useState } from 'react';
import { motion } from 'framer-motion';
import { AppSidebar } from './components/AppSidebar';
import { DashboardHeader } from './components/dashboard/Header';
import { ErrorBoundary } from './components/ErrorBoundary';
import { isTimeoutError, extractApiErrorMessage } from './lib/errors';

// Views
import { DashboardView } from './views/DashboardView';
import { StudioView } from './views/StudioView';
import { ResearchVideoView } from './views/ResearchVideoView';
import { BrandLayoutView } from './views/BrandLayoutView';
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
  const [dubVoiceId, setDubVoiceId] = useState('vi-VN-HoaiMyNeural');
  const [projectName, setProjectName] = useState('');
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
      if (response.data?.title) {
        setProjectName((prev) => prev.trim() || String(response.data.title).slice(0, 120));
      }
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
    if (dubVoiceId) formData.append('voice_id', dubVoiceId);
    const name =
      projectName.trim() ||
      videoInfo?.title?.slice(0, 120) ||
      (file?.name ? file.name.replace(/\.[^.]+$/, '') : '') ||
      '';
    if (name) formData.append('project_name', name);
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
    setProjectName('');
    setFetchError(null);
  };

  const renderView = (view?: string) => {
    const v = view || currentView;
    switch (v) {
      case 'dashboard':
        return (
          <DashboardView 
            targetLang={targetLang}
            setTargetLang={setTargetLang}
            voiceId={dubVoiceId}
            setVoiceId={setDubVoiceId}
            projectName={projectName}
            setProjectName={setProjectName}
            suggestedProjectName={videoInfo?.title || file?.name?.replace(/\.[^.]+$/, '') || ''}
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
      case 'brandLayout':
        return <BrandLayoutView />;
      case 'studio':
        return (
          <StudioView
            targetLang={targetLang}
            setTargetLang={setTargetLang}
            onOpenBrandLayout={() => setCurrentView('brandLayout')}
          />
        );
      case 'researchVideo':
        return (
          <ResearchVideoView
            targetLang={targetLang}
            setTargetLang={setTargetLang}
            onOpenBrandLayout={() => setCurrentView('brandLayout')}
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

  const persistentViews = ['dashboard', 'studio', 'researchVideo', 'shorts', 'brandLayout'] as const;
  const floatingViews = ['editor', 'projects', 'history', 'settings', 'help'] as const;

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
            <div className="max-w-7xl mx-auto h-full">
              <ErrorBoundary>
                <div className="relative min-h-full">
                  {persistentViews.map((viewId) => {
                    const active = currentView === viewId;
                    return (
                      <motion.div
                        key={viewId}
                        initial={false}
                        animate={{
                          opacity: active ? 1 : 0,
                          x: active ? 0 : 24,
                          scale: active ? 1 : 0.985,
                          filter: active ? 'blur(0px)' : 'blur(6px)',
                        }}
                        transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
                        className={
                          active
                            ? 'relative z-10'
                            : 'pointer-events-none absolute inset-0 z-0 overflow-hidden'
                        }
                        aria-hidden={!active}
                      >
                        {renderView(viewId)}
                      </motion.div>
                    );
                  })}

                  {floatingViews.map((viewId) =>
                    currentView === viewId ? (
                      <motion.div
                        key={viewId}
                        initial={{ opacity: 0, y: 18, scale: 0.99 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
                      >
                        {renderView(viewId)}
                      </motion.div>
                    ) : null,
                  )}
                </div>
              </ErrorBoundary>
            </div>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
