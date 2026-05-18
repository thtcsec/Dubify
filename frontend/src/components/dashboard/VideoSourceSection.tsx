import { useState } from 'react';
import { Upload, Info, Trash2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { motion, AnimatePresence } from 'framer-motion';
import { useI18n } from '@/i18n/I18nProvider';

const URL_TABS = ['youtube', 'douyin', 'bilibili', 'kuaishou', 'rednote'] as const;
type UrlTab = (typeof URL_TABS)[number];

interface VideoSourceSectionProps {
  file: File | null;
  setFile: (file: File | null) => void;
  videoUrl: string;
  setVideoUrl: (url: string) => void;
  videoInfo: {
    title: string;
    duration: number;
    thumbnail?: string | null;
    source?: string | null;
  } | null;
  isLoading: boolean;
  onFetchInfo: () => void;
}

export function VideoSourceSection({
  file,
  setFile,
  videoUrl,
  setVideoUrl,
  videoInfo,
  isLoading,
  onFetchInfo,
}: VideoSourceSectionProps) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState('upload');

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    if (value === 'upload') setVideoUrl('');
    else setFile(null);
  };

  const tabLabel: Record<string, string> = {
    upload: t.videoSource.upload,
    youtube: t.videoSource.youtube,
    douyin: t.videoSource.douyin,
    bilibili: t.videoSource.bilibili,
    kuaishou: t.videoSource.kuaishou,
    rednote: t.videoSource.rednote,
  };

  const placeholderFor = (tab: string) =>
    URL_TABS.includes(tab as UrlTab)
      ? t.videoSource.placeholders[tab as UrlTab]
      : t.videoSource.placeholders.default;

  return (
    <Card className="bg-[#111111] border-white/10 text-white overflow-hidden shadow-2xl">
      <motion.div className="flex justify-between items-center p-4 border-b border-white/5">
        <span className="font-semibold text-sm">{t.dashboard.stepSource}</span>
      </motion.div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="w-full flex justify-start bg-transparent border-b border-white/5 rounded-none h-12 px-2 overflow-x-auto no-scrollbar">
          {['upload', ...URL_TABS].map((tab) => (
            <TabsTrigger
              key={tab}
              value={tab}
              className="data-[state=active]:bg-transparent data-[state=active]:text-[#22c55e] text-slate-400 rounded-none border-b-2 border-transparent data-[state=active]:border-[#22c55e] transition-all whitespace-nowrap px-4"
            >
              {tabLabel[tab] ?? tab}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="p-6">
          <motion.div className="bg-[#1a1a1a] border border-amber-500/20 rounded-lg p-3 flex items-start gap-3 mb-6">
            <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-sm text-slate-300">{t.videoSource.noteAudio}</p>
          </motion.div>

          <TabsContent value="upload" className="m-0">
            <div
              className={`border border-dashed rounded-xl p-10 cursor-pointer flex flex-col items-center justify-center gap-4 bg-[#141414] ${
                file ? 'border-[#22c55e]/50 bg-[#22c55e]/5' : 'border-white/10 hover:border-[#22c55e]/50'
              }`}
              onClick={() => document.getElementById('video-upload')?.click()}
            >
              <Upload className="w-8 h-8" />
              <motion.div className="text-center">
                <p className="font-semibold text-sm">{file ? file.name : t.videoSource.dragDrop}</p>
                <p className="text-xs text-slate-500 mt-2">{t.videoSource.supports}</p>
              </motion.div>
              <input
                type="file"
                id="video-upload"
                className="hidden"
                accept="video/*"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </div>
            {file && (
              <div className="flex justify-center mt-4">
                <Button variant="ghost" className="text-red-400 h-9 text-xs" onClick={() => setFile(null)}>
                  <Trash2 className="w-4 h-4 mr-2" /> {t.videoSource.removeFile}
                </Button>
              </div>
            )}
          </TabsContent>

          {URL_TABS.map((tabValue) => (
            <TabsContent key={tabValue} value={tabValue} className="m-0 space-y-4">
              <div className="flex gap-3">
                <Input
                  placeholder={placeholderFor(tabValue)}
                  className="bg-[#141414] border-white/10 h-12 flex-1"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                />
                <Button className="h-12 px-6 bg-[#22c55e]" onClick={onFetchInfo} disabled={!videoUrl || isLoading}>
                  {isLoading ? '...' : t.videoSource.fetchInfo}
                </Button>
              </div>
              <AnimatePresence>
                {videoInfo && !isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="border border-white/10 rounded-xl p-4 bg-[#141414] flex gap-4"
                  >
                    <div className="w-32 aspect-video bg-black rounded-lg overflow-hidden shrink-0">
                      {videoInfo.thumbnail ? (
                        <img src={videoInfo.thumbnail} className="w-full h-full object-cover" alt="" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Info className="w-6 h-6" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0 py-1">
                      <h4 className="font-semibold text-sm truncate">{videoInfo.title}</h4>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-[10px] uppercase text-[#22c55e]">{videoInfo.source}</span>
                        <span className="text-xs text-slate-400">
                          {Math.floor(videoInfo.duration / 60)}:
                          {String(videoInfo.duration % 60).padStart(2, '0')}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </TabsContent>
          ))}
        </div>
      </Tabs>
    </Card>
  );
}
