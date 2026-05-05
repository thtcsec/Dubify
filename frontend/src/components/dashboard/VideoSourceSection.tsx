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
              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Select Video File</Label>
              <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                <div 
                  className={`relative border-2 border-dashed rounded-2xl p-16 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center gap-4 bg-slate-900/80 backdrop-blur-xl ${
                    file ? 'border-blue-500/50 bg-blue-500/10' : 'border-white/10 hover:border-blue-500/50 hover:bg-white/5'
                  }`}
                  onClick={() => document.getElementById('video-upload')?.click()}
                >
                  <div className={`p-4 rounded-2xl transition-transform duration-300 group-hover:scale-110 ${file ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-slate-400 group-hover:bg-blue-500/20 group-hover:text-blue-400'}`}>
                    <Upload className="w-8 h-8" />
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-lg text-slate-200">{file ? file.name : "Drag & drop video here"}</p>
                    <p className="text-sm text-slate-500 mt-2">Supports MP4, MOV, AVI (Max 500MB)</p>
                  </div>
                  <input type="file" id="video-upload" className="hidden" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
                </div>
              </div>
              {file && (
                 <div className="flex justify-center mt-4">
                   <Button variant="ghost" className="text-red-400 hover:text-red-300 hover:bg-red-400/10 transition-colors px-4 py-2 rounded-lg" onClick={(e) => { e.stopPropagation(); setFile(null); }}>
                      <Trash2 className="w-4 h-4 mr-2" /> Remove file
                   </Button>
                 </div>
              )}
           </div>
        </TabsContent>

        <TabsContent value="url" className="p-6 space-y-6">
          <div className="space-y-4">
            <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Enter Video URL</Label>
            <div className="flex gap-3 relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition duration-500"></div>
              <Input 
                placeholder="https://youtube.com/... | bilibili.com/... | vimeo.com/..." 
                className="relative bg-slate-900/80 backdrop-blur-xl border-white/10 focus:border-blue-500/50 h-14 flex-1 rounded-xl text-base px-4 shadow-inner"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
              />
              <Button 
                className="relative h-14 px-8 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 font-bold shadow-[0_0_15px_rgba(59,130,246,0.3)] hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] transition-all"
                onClick={onFetchInfo} 
                disabled={!videoUrl || isLoading}
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                ) : (
                  "Fetch Info"
                )}
              </Button>
            </div>
          </div>

          <AnimatePresence>
            {videoInfo && !isLoading && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="border border-white/10 rounded-xl p-4 bg-slate-900/80 backdrop-blur-xl shadow-2xl flex gap-5">
                 <div className="w-40 aspect-video bg-black rounded-lg overflow-hidden shrink-0 border border-white/5 relative group cursor-pointer shadow-lg">
                   {videoInfo.thumbnail ? (
                     <img src={videoInfo.thumbnail} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" alt="thumbnail" />
                   ) : (
                     <div className="w-full h-full flex items-center justify-center text-slate-600"><Info /></div>
                   )}
                   <div className="absolute inset-0 ring-1 ring-inset ring-black/10"></div>
                 </div>
                 <div className="flex-1 min-w-0 py-1 flex flex-col justify-center">
                    <h4 className="font-bold text-lg text-white truncate group-hover:text-blue-400 transition-colors">{videoInfo.title}</h4>
                    <div className="flex items-center gap-3 mt-3">
                      <span className="text-xs font-semibold bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full border border-blue-500/20">
                        {videoInfo.source}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        {Math.floor(videoInfo.duration / 60)}:{String(videoInfo.duration % 60).padStart(2, '0')}
                      </span>
                    </div>
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
