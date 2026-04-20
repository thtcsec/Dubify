import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { VideoSourceSection } from '@/components/dashboard/VideoSourceSection';
import { ProjectSettings } from '@/components/dashboard/ProjectSettings';
import { DubbingProgress } from '@/components/DubbingProgress';

interface DashboardViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
  jobId: string | null;
  setJobId: (id: string | null) => void;
  isLoading: boolean;
  file: File | null;
  setFile: (file: File | null) => void;
  videoUrl: string;
  setVideoUrl: (url: string) => void;
  videoInfo: any;
  handleFetchInfo: () => void;
  handleStartDubbing: () => void;
  resetProject: () => void;
}

export function DashboardView({
  targetLang,
  setTargetLang,
  jobId,
  setJobId,
  isLoading,
  file,
  setFile,
  videoUrl,
  setVideoUrl,
  videoInfo,
  handleFetchInfo,
  handleStartDubbing,
  resetProject
}: DashboardViewProps) {
  return (
    <>
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
