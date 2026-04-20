import { useState } from 'react';
import { DubbingProgress } from './components/DubbingProgress';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Upload, Languages, Sparkles, Link as LinkIcon, Info, Play, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  SidebarProvider, 
  SidebarInset, 
  SidebarTrigger 
} from '@/components/ui/sidebar';
import { AppSidebar } from './components/AppSidebar';
import api from './lib/api';

const LANGUAGES = [
  { code: 'vi', name: 'Vietnamese' },
  { code: 'en', name: 'English' },
  { code: 'ru', name: 'Russian' },
  { code: 'de', name: 'German' },
  { code: 'fr', name: 'French' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ja', name: 'Japanese' },
];

export default function App() {
  // Common state
  const [targetLang, setTargetLang] = useState('vi');
  const [jobId, setJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // File Upload state
  const [file, setFile] = useState<File | null>(null);

  // URL state
  const [videoUrl, setVideoUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<any>(null);

  const handleFileUpload = async () => {
    if (!file) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_lang', targetLang);
    try {
      const response = await api.post('/dub', formData);
      setJobId(response.data.job_id);
    } catch (err) {
      alert('Upload failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchInfo = async () => {
    if (!videoUrl) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append('url', videoUrl);
    try {
      const response = await api.post('/fetch-info', formData);
      setVideoInfo(response.data);
    } catch (err) {
      alert('Failed to fetch video info. Make sure the URL is public.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDubUrl = async () => {
    if (!videoUrl) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append('url', videoUrl);
    formData.append('target_lang', targetLang);
    try {
      const response = await api.post('/dub-url', formData);
      setJobId(response.data.job_id);
    } catch (err) {
      alert('Request failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="bg-slate-950">
        <header className="flex h-16 shrink-0 items-center gap-2 border-b border-white/5 px-4 sticky top-0 bg-slate-950/80 backdrop-blur-md z-12">
          <SidebarTrigger className="-ml-1 text-slate-400" />
          <div className="h-4 w-px bg-white/10 mx-2" />
          <div className="flex items-center gap-2 text-sm font-medium">
             <span className="text-slate-400">Dashboard</span>
             <span className="text-slate-600">/</span>
             <span className="text-white">Create New Project</span>
          </div>
        </header>

        <div className="p-8 max-w-5xl mx-auto w-full">
          {!jobId && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
               <h1 className="text-3xl font-bold mb-2">Create New Dubbing Project</h1>
               <p className="text-slate-400 mb-8">Upload a local file or import from a URL.</p>
            </motion.div>
          )}

          <main>
            <AnimatePresence mode="wait">
              {!jobId ? (
                <motion.div key="creation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column: Input */}
                    <div className="lg:col-span-2 space-y-6">
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
                                  placeholder="https://youtube.com/watch?v=... or Twitter/Douyin link" 
                                  className="bg-white/5 border-white/10 h-12 flex-1"
                                  value={videoUrl}
                                  onChange={(e) => setVideoUrl(e.target.value)}
                                />
                                <Button className="h-12 px-6" onClick={handleFetchInfo} disabled={!videoUrl || isLoading}>
                                  {isLoading ? "Fetching..." : "Fetch Info"}
                                </Button>
                              </div>
                              <div className="flex items-center gap-4 text-xs text-slate-500">
                                 <span className="flex items-center gap-1"><Play className="w-3 h-3" /> YouTube</span>
                                 <span className="flex items-center gap-1"><Play className="w-3 h-3" /> Twitter (X)</span>
                                 <span className="flex items-center gap-1"><Play className="w-3 h-3" /> Douyin</span>
                                 <span className="flex items-center gap-1"><Play className="w-3 h-3" /> Google Drive</span>
                              </div>
                            </div>

                            <AnimatePresence>
                              {videoInfo && !isLoading && (
                                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="border border-white/10 rounded-lg p-4 bg-white/5 flex gap-4">
                                   <div className="w-32 aspect-video bg-slate-800 rounded overflow-hidden shrink-0">
                                     {videoInfo.thumbnail ? (
                                       <img src={videoInfo.thumbnail} className="w-full h-full object-cover" />
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
                    </div>

                    {/* Right Column: Settings */}
                    <div className="space-y-6">
                      <Card className="bg-white/5 border-white/10 text-white shadow-xl">
                        <CardHeader>
                          <CardTitle className="text-lg">Project Settings</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                          <div className="space-y-2">
                            <Label className="text-slate-400">Target Language</Label>
                            <Select value={targetLang} onValueChange={setTargetLang}>
                              <SelectTrigger className="bg-white/10 border-white/10">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {LANGUAGES.map(lang => (
                                  <SelectItem key={lang.code} value={lang.code}>{lang.name}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="pt-4 space-y-4">
                            <Button 
                              className="w-full h-14 text-lg font-bold shadow-lg shadow-primary/30" 
                              disabled={isLoading || (!file && !videoInfo)}
                              onClick={file ? handleFileUpload : handleDubUrl}
                            >
                              <Sparkles className="w-5 h-5 mr-2" /> Start Dubbing
                            </Button>
                            <p className="text-[10px] text-center text-slate-500">
                              Estimated time: 3-5 mins depending on hardware
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div key="progress" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
                   <div className="flex items-center justify-between mb-8">
                      <Button variant="ghost" className="text-slate-400" onClick={() => { setJobId(null); setVideoInfo(null); setFile(null); }}>
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
