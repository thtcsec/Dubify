import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { DubbingProgress } from '../components/DubbingProgress';
import { isTimeoutError, extractApiErrorMessage } from '../lib/errors';
import api from '../lib/api';

interface Voice {
  id: string;
  name: string;
  lang: string;
  gender: string;
}

const ASPECT_RATIO_OPTIONS = [
  { value: '16:9', label: '16:9 Landscape' },
  { value: '4:3', label: '4:3 Classic' },
  { value: '9:16', label: '9:16 Vertical' },
  { value: '3:4', label: '3:4 Portrait' },
  { value: '1:1', label: '1:1 Square' },
];

interface StudioViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
}

export function StudioView({ targetLang, setTargetLang }: StudioViewProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [newsText, setNewsText] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [aspectRatio, setAspectRatio] = useState('16:9');
  
  // Voice
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural');
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api.get('/voices').then(res => setVoices(res.data)).catch(() => {});
  }, []);

  // Estimated duration: ~150 words per minute for TTS
  const wordCount = newsText.trim().split(/\s+/).filter(Boolean).length;
  const autoEstimatedDuration = Math.max(Math.ceil((wordCount / 150) * 60), 0);
  const [manualDuration, setManualDuration] = useState<number | null>(null);
  const estimatedDuration = manualDuration !== null ? manualDuration : autoEstimatedDuration;

  const handlePreviewVoice = async () => {
    if (isPreviewPlaying) {
      audioRef.current?.pause();
      setIsPreviewPlaying(false);
      return;
    }
    setIsPreviewPlaying(true);
    try {
      const formData = new FormData();
      formData.append('voice_id', selectedVoice);
      formData.append('text', newsText.substring(0, 200) || 'Xin chào, đây là bản xem trước giọng nói.');
      const response = await api.post('/voice-preview', formData, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      if (audioRef.current) { audioRef.current.pause(); }
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setIsPreviewPlaying(false);
      audio.play();
    } catch {
      setError('Failed to preview voice.');
      setIsPreviewPlaying(false);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      applyImageFile(e.target.files[0]);
    }
  };

  const applyImageFile = (file: File) => {
    setImageFile(file);
    setImageUrl(null);
    setImagePreview(URL.createObjectURL(file));
    setError(null);
  };

  const applyRemoteImage = (url: string) => {
    setImageFile(null);
    setImageUrl(url);
    setImagePreview(url);
    setError(null);
  };

  const tryExtractImageUrl = (dataTransfer: DataTransfer): string | null => {
    const uriList = dataTransfer.getData('text/uri-list');
    if (uriList) {
      const firstUrl = uriList.split('\n').map((item) => item.trim()).find((item) => item && !item.startsWith('#'));
      if (firstUrl) return firstUrl;
    }

    const plainText = dataTransfer.getData('text/plain').trim();
    if (/^https?:\/\//i.test(plainText)) {
      return plainText;
    }

    const html = dataTransfer.getData('text/html');
    if (html) {
      const match = html.match(/<img[^>]+src=["']([^"']+)["']/i);
      if (match?.[1]) {
        return match[1];
      }
    }

    return null;
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);

    const file = Array.from(event.dataTransfer.files).find((item) => item.type.startsWith('image/'));
    if (file) {
      applyImageFile(file);
      return;
    }

    const droppedUrl = tryExtractImageUrl(event.dataTransfer);
    if (droppedUrl) {
      applyRemoteImage(droppedUrl);
      return;
    }

    setError('Please drop an image file or an online image URL.');
  };

  const handleGenerate = async () => {
    if (!newsText.trim() || (!imageFile && !imageUrl)) {
        setError("Please provide both news text and a background image.");
        return;
    }
    
    setIsLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('text', newsText);
    if (imageFile) {
      formData.append('image', imageFile);
    }
    if (imageUrl) {
      formData.append('image_url', imageUrl);
    }
    formData.append('target_lang', targetLang);
    formData.append('voice_id', selectedVoice);
    formData.append('aspect_ratio', aspectRatio);
    if (manualDuration !== null && manualDuration > 0) {
      formData.append('duration_seconds', String(manualDuration));
    }
    
    try {
      const response = await api.post('/studio', formData);
      setJobId(response.data.job_id);
    } catch (err) {
      if (isTimeoutError(err)) {
         setError('Studio job generation timed out.');
      } else {
         setError(extractApiErrorMessage(err, 'Failed to start News Studio generation.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const resetStudio = () => {
    setJobId(null);
    setNewsText('');
    setImageFile(null);
    setImageUrl(null);
    setImagePreview('');
    setAspectRatio('16:9');
    setError(null);
    setManualDuration(null);
    if (audioRef.current) audioRef.current.pause();
  };

  const filteredVoices = voices.filter(v => v.lang === targetLang || voices.length === 0);
  const displayVoices = filteredVoices.length > 0 ? filteredVoices : voices;
  const previewAspectRatio = aspectRatio.replace(':', ' / ');
  const previewFrameClass = aspectRatio === '9:16' || aspectRatio === '3:4'
    ? 'max-w-[420px]'
    : aspectRatio === '1:1'
      ? 'max-w-[540px]'
      : 'max-w-[760px]';

  return (
    <>
      {!jobId && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
           <h1 className="text-3xl font-bold mb-2">Script to Video</h1>
           <p className="text-slate-400 mb-8">Turn a script and background into a narrated social video, with drag-drop image input, canvas ratio control, and auto caption overlays.</p>
        </motion.div>
      )}

      <main>
        <AnimatePresence mode="wait">
          {!jobId ? (
            <motion.div key="creation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                   <div className="flex items-center gap-3">
                      <div className="p-2 bg-red-500/20 rounded-full text-red-400">
                         <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                      </div>
                      <p className="text-red-400/80 text-sm">{error}</p>
                   </div>
                </div>
              )}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                {/* Content Input Column */}
                <div className="lg:col-span-7 space-y-8">
                  <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
                      <div className="flex items-center justify-between mb-4">
                        <Label className="text-lg font-bold flex items-center gap-2">
                          <span className="bg-indigo-500/20 text-indigo-400 p-1.5 rounded-lg">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                          </span>
                          Script Content
                        </Label>
                        {wordCount > 0 && (
                          <span className="text-xs font-mono bg-indigo-500/10 text-indigo-300 px-3 py-1 rounded-full border border-indigo-500/20">
                            {wordCount} words · ~{estimatedDuration}s
                          </span>
                        )}
                      </div>
                      <Textarea 
                        placeholder="Write or paste your script here. Our AI will automatically synthesize this into professional narration..."
                        className="min-h-[180px] bg-black/40 border-white/5 focus:border-indigo-500/50 rounded-xl transition-all resize-none text-base placeholder:text-slate-600 focus:ring-1 focus:ring-indigo-500/50"
                        value={newsText}
                        onChange={(e) => setNewsText(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
                      <Label className="text-lg font-bold mb-4 flex items-center gap-2">
                        <span className="bg-blue-500/20 text-blue-400 p-1.5 rounded-lg">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        </span>
                        Background Visual
                      </Label>
                      <div
                        className="relative"
                        onDragOver={(event) => {
                          event.preventDefault();
                          setIsDragOver(true);
                        }}
                        onDragLeave={() => setIsDragOver(false)}
                        onDrop={handleDrop}
                      >
                          {imagePreview ? (
                              <div
                                className={`relative mx-auto w-full rounded-xl overflow-hidden border-2 bg-black ${previewFrameClass} ${isDragOver ? 'border-blue-400 ring-4 ring-blue-500/30' : 'border-white/10'}`}
                                style={{ aspectRatio: previewAspectRatio }}
                              >
                                  <img src={imagePreview} alt="Background" className="w-full h-full object-cover opacity-90 transition-transform duration-700 hover:scale-105" />
                                  <div className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 hover:opacity-100 transition-opacity backdrop-blur-sm">
                                      <div className="flex flex-col items-center gap-4">
                                        <Label htmlFor="image-upload" className="cursor-pointer bg-white/10 hover:bg-white/20 backdrop-blur-md px-6 py-3 rounded-xl text-white font-semibold transition-all hover:scale-105 border border-white/20 shadow-xl">
                                            Replace Image
                                        </Label>
                                        {imageUrl && (
                                          <span className="max-w-[80%] truncate text-xs text-slate-300 bg-black/50 px-3 py-1 rounded-full border border-white/10">
                                            URL: {imageUrl}
                                          </span>
                                        )}
                                      </div>
                                  </div>
                              </div>
                          ) : (
                              <Label 
                                  htmlFor="image-upload" 
                                  className={`mx-auto flex w-full flex-col items-center justify-center border-2 border-dashed rounded-xl bg-black/40 transition-all duration-300 cursor-pointer group ${previewFrameClass} ${
                                    isDragOver ? 'border-blue-400 bg-blue-900/20 scale-[1.02]' : 'border-white/20 hover:bg-white/5 hover:border-blue-500/50'
                                  }`}
                                  style={{ aspectRatio: previewAspectRatio }}
                              >
                                  <div className="p-5 bg-white/5 rounded-2xl mb-4 text-slate-400 group-hover:text-blue-400 group-hover:bg-blue-500/10 transition-colors group-hover:scale-110 duration-300">
                                     <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                                  </div>
                                  <span className="text-base font-semibold text-slate-200">Drag & drop your visual</span>
                                  <span className="text-sm text-slate-500 mt-2">or click to browse from your computer</span>
                              </Label>
                          )}
                          <input id="image-upload" type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Settings & Generation Column */}
                <div className="lg:col-span-5 space-y-8">
                  <div className="relative group h-full flex flex-col">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl flex-1 flex flex-col">
                      <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                          <span className="bg-purple-500/20 text-purple-400 p-1.5 rounded-lg">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                          </span>
                          Configuration
                      </h3>
                      
                      <div className="space-y-6 flex-1">
                          {/* Language */}
                          <div className="space-y-2.5">
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Target Language</Label>
                              <Select value={targetLang} onValueChange={(v) => {
                                setTargetLang(v);
                                const firstMatch = voices.find(voice => voice.lang === v);
                                if (firstMatch) setSelectedVoice(firstMatch.id);
                              }}>
                              <SelectTrigger className="w-full bg-black/40 border-white/10 hover:border-white/20 transition-colors h-11 rounded-xl">
                                  <SelectValue placeholder="Select language" />
                              </SelectTrigger>
                              <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                                  <SelectItem value="vi">🇻🇳 Vietnamese</SelectItem>
                                  <SelectItem value="en">🇺🇸 English</SelectItem>
                                  <SelectItem value="ja">🇯🇵 Japanese</SelectItem>
                                  <SelectItem value="ko">🇰🇷 Korean</SelectItem>
                                  <SelectItem value="zh">🇨🇳 Chinese</SelectItem>
                                  <SelectItem value="fr">🇫🇷 French</SelectItem>
                                  <SelectItem value="es">🇪🇸 Spanish</SelectItem>
                                  <SelectItem value="de">🇩🇪 German</SelectItem>
                              </SelectContent>
                              </Select>
                          </div>

                          {/* Voice */}
                          <div className="space-y-2.5">
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">AI Voice Model</Label>
                              <div className="flex gap-2">
                                <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                                <SelectTrigger className="flex-1 bg-black/40 border-white/10 hover:border-white/20 transition-colors h-11 rounded-xl">
                                    <SelectValue placeholder="Select voice" />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                                    {displayVoices.map(v => (
                                      <SelectItem key={v.id} value={v.id}>
                                        <div className="flex items-center gap-2">
                                          <span className={`w-2 h-2 rounded-full ${v.gender === 'Female' ? 'bg-pink-500' : 'bg-blue-500'}`}></span>
                                          {v.name}
                                        </div>
                                      </SelectItem>
                                    ))}
                                </SelectContent>
                                </Select>
                                <Button 
                                  variant="outline" 
                                  className="h-11 w-11 shrink-0 rounded-xl bg-black/40 border-white/10 hover:bg-purple-500/20 hover:border-purple-500/50 hover:text-purple-400 transition-all"
                                  onClick={handlePreviewVoice}
                                  title="Preview voice"
                                >
                                  {isPreviewPlaying ? (
                                    <svg className="w-4 h-4 animate-pulse" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                                  ) : (
                                    <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                                  )}
                                </Button>
                              </div>
                          </div>

                          <div className="space-y-2.5">
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Canvas Format</Label>
                              <Select value={aspectRatio} onValueChange={setAspectRatio}>
                                <SelectTrigger className="w-full bg-black/40 border-white/10 hover:border-white/20 transition-colors h-11 rounded-xl">
                                  <SelectValue placeholder="Select aspect ratio" />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                                  {ASPECT_RATIO_OPTIONS.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                      {option.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                          </div>

                          {/* Duration estimate */}
                          {wordCount > 0 && (
                            <div className="bg-black/30 rounded-xl p-4 border border-white/5 space-y-3">
                              <div className="flex items-center justify-between">
                                <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Timing Control</Label>
                                <span className="bg-purple-500/10 text-purple-400 font-mono font-bold px-2 py-0.5 rounded text-sm border border-purple-500/20">
                                  {Math.floor(estimatedDuration / 60)}:{String(estimatedDuration % 60).padStart(2, '0')}
                                </span>
                              </div>
                              <div className="flex items-center gap-3">
                                <input
                                  type="range"
                                  min={5}
                                  max={Math.max(300, autoEstimatedDuration * 2)}
                                  value={estimatedDuration}
                                  onChange={(e) => setManualDuration(Number(e.target.value))}
                                  className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                />
                                <input
                                  type="number"
                                  min={5}
                                  max={600}
                                  value={estimatedDuration}
                                  onChange={(e) => setManualDuration(Number(e.target.value) || 0)}
                                  className="w-16 bg-black/50 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-center font-mono text-purple-400 focus:border-purple-500/50 outline-none"
                                />
                              </div>
                              {manualDuration !== null && (
                                <div className="text-right">
                                  <button
                                    onClick={() => setManualDuration(null)}
                                    className="text-[11px] text-slate-500 hover:text-purple-400 transition-colors font-medium"
                                  >
                                    Reset to auto ({autoEstimatedDuration}s)
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                      </div>

                      <div className="pt-6 mt-6 border-t border-white/10">
                          <Button 
                              className="w-full btn-glow bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-7 rounded-xl text-lg shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_25px_rgba(79,70,229,0.5)] transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]" 
                              disabled={isLoading}
                              onClick={handleGenerate}
                          >
                              {isLoading ? (
                                  <div className="flex items-center justify-center gap-3">
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                    <span>Synthesizing...</span>
                                  </div>
                              ) : (
                                  <span className="flex items-center gap-2">
                                      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M19.376 12.416L8.777 19.482A.5.5 0 018 19.066V4.934a.5.5 0 01.777-.416l10.599 7.066a.5.5 0 010 .832z"/></svg>
                                      Generate Studio Video
                                  </span>
                              )}
                          </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            </motion.div>
          ) : (
            <motion.div key="progress" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
               <div className="flex items-center justify-between mb-8">
                  <Button variant="ghost" className="text-slate-400" onClick={resetStudio}>
                    ← Back to Studio Editor
                  </Button>
                  <div className="text-sm text-slate-500">Job ID: <span className="text-slate-300 font-mono">{jobId}</span></div>
               </div>
               <DubbingProgress 
                jobId={jobId} 
                onComplete={() => console.log('Job completed!')}
                onError={(err) => console.error('Job failed:', err)}
               />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </>
  );
}
