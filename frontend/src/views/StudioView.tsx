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

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                
                {/* Editor Column */}
                <div className="lg:col-span-8 space-y-6">
                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-3">
                      <Label className="text-base font-semibold">1. News Context</Label>
                      {wordCount > 0 && (
                        <span className="text-xs text-slate-500">
                          {wordCount} words · ~{estimatedDuration}s video
                        </span>
                      )}
                    </div>
                    <Textarea 
                      placeholder="Paste your breaking news article or raw information here. Our LLM will rewrite it into a broadcast-ready script..."
                      className="min-h-[200px] bg-slate-950/50 border-slate-800 focus:border-indigo-500 transition-colors"
                      value={newsText}
                      onChange={(e) => setNewsText(e.target.value)}
                    />
                  </div>

                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <Label className="text-base font-semibold mb-3 block">2. Background Visual</Label>
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
                              className={`relative mx-auto w-full rounded-lg overflow-hidden border bg-slate-950 ${previewFrameClass} ${isDragOver ? 'border-indigo-400 ring-2 ring-indigo-500/40' : 'border-slate-700'}`}
                              style={{ aspectRatio: previewAspectRatio }}
                            >
                                <img src={imagePreview} alt="Background" className="w-full h-full object-cover opacity-80" />
                                <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 hover:opacity-100 transition-opacity">
                                    <div className="flex flex-col items-center gap-3">
                                      <Label htmlFor="image-upload" className="cursor-pointer bg-white/10 hover:bg-white/20 backdrop-blur-md px-4 py-2 rounded-lg text-white font-medium transition-colors">
                                          Change Image
                                      </Label>
                                      {imageUrl && (
                                        <span className="max-w-[80%] truncate text-xs text-slate-200">
                                          Remote image: {imageUrl}
                                        </span>
                                      )}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <Label 
                                htmlFor="image-upload" 
                                className={`mx-auto flex w-full flex-col items-center justify-center border-2 border-dashed rounded-lg bg-slate-950/50 transition-colors cursor-pointer group ${previewFrameClass} ${
                                  isDragOver ? 'border-indigo-400 bg-slate-900/80' : 'border-slate-800 hover:bg-slate-900/50 hover:border-indigo-500/50'
                                }`}
                                style={{ aspectRatio: previewAspectRatio }}
                            >
                                <div className="p-4 bg-slate-800/50 rounded-full mb-4 text-slate-400 group-hover:text-indigo-400 transition-colors">
                                   <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                                </div>
                                <span className="text-sm font-medium text-slate-300">Click or drop a background image</span>
                                <span className="text-xs text-slate-500 mt-1">PNG, JPG up to 10MB, or drag an image from another website</span>
                            </Label>
                        )}
                        <input id="image-upload" type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                    </div>
                  </div>
                </div>

                {/* Settings Column */}
                <div className="lg:col-span-4 space-y-6">
                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        Studio Settings
                    </h3>
                    
                    <div className="space-y-4">
                        {/* Language */}
                        <div className="space-y-2">
                            <Label className="text-slate-400 text-xs uppercase tracking-wider">Language</Label>
                            <Select value={targetLang} onValueChange={(v) => {
                              setTargetLang(v);
                              // Auto-select a voice for the new language
                              const firstMatch = voices.find(voice => voice.lang === v);
                              if (firstMatch) setSelectedVoice(firstMatch.id);
                            }}>
                            <SelectTrigger className="w-full bg-slate-950 border-slate-800">
                                <SelectValue placeholder="Select language" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-900 border-slate-800">
                                <SelectItem value="vi">🇻🇳 Vietnamese</SelectItem>
                                <SelectItem value="en">🇺🇸 English</SelectItem>
                                <SelectItem value="ja">🇯🇵 Japanese</SelectItem>
                                <SelectItem value="ko">🇰🇷 Korean</SelectItem>
                                <SelectItem value="zh">🇨🇳 Chinese</SelectItem>
                                <SelectItem value="fr">🇫🇷 French</SelectItem>
                                <SelectItem value="es">🇪🇸 Spanish</SelectItem>
                                <SelectItem value="de">🇩🇪 German</SelectItem>
                                <SelectItem value="pt">🇧🇷 Portuguese</SelectItem>
                                <SelectItem value="it">🇮🇹 Italian</SelectItem>
                                <SelectItem value="ru">🇷🇺 Russian</SelectItem>
                                <SelectItem value="th">🇹🇭 Thai</SelectItem>
                                <SelectItem value="hi">🇮🇳 Hindi</SelectItem>
                                <SelectItem value="ar">🇸🇦 Arabic</SelectItem>
                                <SelectItem value="id">🇮🇩 Indonesian</SelectItem>
                            </SelectContent>
                            </Select>
                        </div>

                        {/* Voice */}
                        <div className="space-y-2">
                            <Label className="text-slate-400 text-xs uppercase tracking-wider">Voice</Label>
                            <div className="flex gap-2">
                              <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                              <SelectTrigger className="flex-1 bg-slate-950 border-slate-800">
                                  <SelectValue placeholder="Select voice" />
                              </SelectTrigger>
                              <SelectContent className="bg-slate-900 border-slate-800">
                                  {displayVoices.map(v => (
                                    <SelectItem key={v.id} value={v.id}>
                                      {v.gender === 'Female' ? '♀' : '♂'} {v.name} ({v.lang})
                                    </SelectItem>
                                  ))}
                              </SelectContent>
                              </Select>
                              <Button 
                                variant="outline" 
                                size="icon"
                                className="border-slate-800 hover:bg-indigo-500/20 hover:border-indigo-500/50 shrink-0"
                                onClick={handlePreviewVoice}
                                title="Preview voice"
                              >
                                {isPreviewPlaying ? (
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                                ) : (
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>
                                )}
                              </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-slate-400 text-xs uppercase tracking-wider">Canvas Ratio</Label>
                            <Select value={aspectRatio} onValueChange={setAspectRatio}>
                              <SelectTrigger className="w-full bg-slate-950 border-slate-800">
                                <SelectValue placeholder="Select aspect ratio" />
                              </SelectTrigger>
                              <SelectContent className="bg-slate-900 border-slate-800">
                                {ASPECT_RATIO_OPTIONS.map((option) => (
                                  <SelectItem key={option.value} value={option.value}>
                                    {option.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                        </div>

                        {/* Duration estimate — editable */}
                        {wordCount > 0 && (
                          <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800 space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-slate-500">Est. Duration (seconds)</span>
                              <span className="text-indigo-400 font-mono font-bold">
                                {Math.floor(estimatedDuration / 60)}:{String(estimatedDuration % 60).padStart(2, '0')}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <input
                                type="range"
                                min={5}
                                max={Math.max(300, autoEstimatedDuration * 2)}
                                value={estimatedDuration}
                                onChange={(e) => setManualDuration(Number(e.target.value))}
                                className="flex-1 accent-indigo-500 h-1.5"
                              />
                              <input
                                type="number"
                                min={5}
                                max={600}
                                value={estimatedDuration}
                                onChange={(e) => setManualDuration(Number(e.target.value) || 0)}
                                className="w-16 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-center font-mono text-indigo-400"
                              />
                            </div>
                            {manualDuration !== null && (
                              <button
                                onClick={() => setManualDuration(null)}
                                className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
                              >
                                Reset to auto ({autoEstimatedDuration}s)
                              </button>
                            )}
                          </div>
                        )}
                    </div>

                    <div className="pt-6 mt-6 border-t border-slate-800">
                        <Button 
                            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-6 rounded-lg transition-all transform active:scale-[0.98]" 
                            disabled={isLoading}
                            onClick={handleGenerate}
                        >
                            {isLoading ? (
                                <div className="flex items-center justify-center gap-2">
                                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                  </svg>
                                  <span>Brewing Video...</span>
                                </div>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                    Generate News Video
                                </span>
                            )}
                        </Button>
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
