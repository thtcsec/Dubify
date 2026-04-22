import { Upload, Link as LinkIcon, Info, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { motion, AnimatePresence } from 'framer-motion';

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
  onFetchInfo
}: VideoSourceSectionProps) {
  return (
    <Card className="bg-white/5 border-white/10 text-white overflow-hidden shadow-2xl">
      <Tabs defaultValue="upload" className="w-full">
        <TabsList className="w-full grid grid-cols-2 bg-transparent border-b border-white/5 rounded-none h-14">
          <TabsTrigger value="upload" className="data-[state=active]:bg-white/5 data-[state=active]:text-primary rounded-none border-b-2 border-transparent data-[state=active]:border-primary transition-all">
            <Upload className="w-4 h-4 mr-2" /> Local Upload
          </TabsTrigger>
          <TabsTrigger value="url" className="data-[state=active]:bg-white/5 data-[state=active]:text-primary rounded-none border-b-2 border-transparent data-[state=active]:border-primary transition-all">
            <LinkIcon className="w-4 h-4 mr-2" /> Import from URL
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="upload" className="p-6">
           <div className="space-y-4">
              <Label className="text-slate-400">Select Video File</Label>
              <div 
                className={`border-2 border-dashed rounded-xl p-16 transition-all cursor-pointer flex flex-col items-center justify-center gap-4 ${
                  file ? 'border-primary bg-primary/5' : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                }`}
                onClick={() => document.getElementById('video-upload')?.click()}
              >
                <Upload className={`w-12 h-12 ${file ? 'text-primary' : 'text-slate-600'}`} />
                <div className="text-center">
                  <p className="font-semibold text-lg">{file ? file.name : "Drop video here or click to upload"}</p>
                  <p className="text-sm text-slate-500">Supports MP4, MOV, AVI (Max 500MB)</p>
                </div>
                <input type="file" id="video-upload" className="hidden" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              </div>
              {file && (
                 <Button variant="ghost" className="text-red-400 hover:text-red-300 h-8 p-0" onClick={(e) => { e.stopPropagation(); setFile(null); }}>
                    <Trash2 className="w-4 h-4 mr-2" /> Remove file
                 </Button>
              )}
           </div>
        </TabsContent>

        <TabsContent value="url" className="p-6 space-y-6">
          <div className="space-y-4">
            <Label className="text-slate-400">Enter Video URL</Label>
            <div className="flex gap-2">
              <Input 
                placeholder="https://youtube.com/... | https://www.bilibili.com/video/BV... | https://drive.google.com/..." 
                className="bg-white/5 border-white/10 h-12 flex-1"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
              />
              <Button className="h-12 px-6" onClick={onFetchInfo} disabled={!videoUrl || isLoading}>
                {isLoading ? "Fetching..." : "Fetch Info"}
              </Button>
            </div>
          </div>

          <AnimatePresence>
            {videoInfo && !isLoading && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="border border-white/10 rounded-lg p-4 bg-white/5 flex gap-4">
                 <div className="w-32 aspect-video bg-slate-800 rounded overflow-hidden shrink-0">
                   {videoInfo.thumbnail ? (
                     <img src={videoInfo.thumbnail} className="w-full h-full object-cover" alt="thumbnail" />
                   ) : (
                     <div className="w-full h-full flex items-center justify-center text-slate-600"><Info /></div>
                   )}
                 </div>
                 <div className="flex-1 min-w-0">
                    <h4 className="font-bold truncate">{videoInfo.title}</h4>
                    <p className="text-xs text-slate-500 mt-1">
                      Source: <span className="text-primary">{videoInfo.source}</span> &bull; 
                      Duration: {videoInfo.duration}s
                    </p>
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
