import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { VideoSourceSection } from '@/components/dashboard/VideoSourceSection';
import { ProjectSettings } from '@/components/dashboard/ProjectSettings';
import { DubbingProgress } from '@/components/DubbingProgress';
import { useI18n } from '@/i18n/I18nProvider';

interface DashboardViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
  jobId: string | null;
  isLoading: boolean;
  file: File | null;
  setFile: (file: File | null) => void;
  videoUrl: string;
  setVideoUrl: (url: string) => void;
  videoInfo: {
    title: string;
    duration: number;
    thumbnail?: string | null;
    source?: string | null;
    url?: string;
  } | null;
  fetchError: string | null;
  handleFetchInfo: () => void;
  handleStartDubbing: () => void;
  resetProject: () => void;
}

export function DashboardView({
  targetLang,
  setTargetLang,
  jobId,
  isLoading,
  file,
  setFile,
  videoUrl,
  setVideoUrl,
  videoInfo,
  fetchError,
  handleFetchInfo,
  handleStartDubbing,
  resetProject
}: DashboardViewProps) {
  const { t } = useI18n();
  return (
    <>
      {!jobId && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
           <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
             <span className="bg-gradient-to-br from-blue-500 to-indigo-500 text-transparent bg-clip-text">{t.dashboard.title}</span>
             <span className="bg-blue-500/10 text-blue-400 text-xs px-2 py-1 rounded border border-blue-500/20 font-mono tracking-widest uppercase">{t.dashboard.badge}</span>
           </h1>
           <p className="text-slate-400">{t.dashboard.subtitle}</p>
        </motion.div>
      )}

      <main>
        <AnimatePresence mode="wait">
          {!jobId ? (
            <motion.div key="creation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              
              {fetchError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-center justify-between">
                   <div className="flex items-center gap-3">
                      <div className="p-2 bg-red-500/20 rounded-full text-red-400">
                         <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                      </div>
                      <div>
                         <h4 className="text-red-400 font-semibold text-sm">{t.dashboard.connectionError}</h4>
                         <p className="text-red-400/80 text-xs">{fetchError}</p>
                      </div>
                   </div>
                   <Button variant="outline" size="sm" onClick={videoUrl ? handleFetchInfo : handleStartDubbing} className="border-red-500/20 text-red-400 hover:bg-red-500/10">
                      {t.dashboard.retry}
                   </Button>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
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
    </>
  );
}
