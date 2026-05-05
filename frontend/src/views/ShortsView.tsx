import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { DubbingProgress } from '../components/DubbingProgress';
import { isTimeoutError, extractApiErrorMessage } from '../lib/errors';
import api from '../lib/api';

interface Voice {
  id: string;
  name: string;
  lang: string;
  gender: string;
}

const LANGUAGE_OPTIONS = [
  { value: 'vi', label: 'Vietnamese' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'zh', label: 'Chinese' },
  { value: 'fr', label: 'French' },
  { value: 'es', label: 'Spanish' },
  { value: 'de', label: 'German' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'it', label: 'Italian' },
  { value: 'ru', label: 'Russian' },
  { value: 'th', label: 'Thai' },
  { value: 'hi', label: 'Hindi' },
  { value: 'ar', label: 'Arabic' },
  { value: 'id', label: 'Indonesian' },
];

interface ShortsViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
}

const MODEL_OPTIONS = [
  {
    value: 'local',
    name: 'Local (Fast Render)',
    description: 'No external API. Gradient background + caption-first render. Fast and free, but not AI video generation.',
    requiresKey: false,
  },
  {
    value: 'veo3',
    name: 'Google Veo 3.1 (fal.ai)',
    description: 'Reviewers highlight strong cinematic realism and audio sync, but it is pricey and can miss precise details.',
    requiresKey: true,
  },
  {
    value: 'kling',
    name: 'Kling 3.0 (fal.ai)',
    description: 'Known for cinematic multi-shot control and realistic motion. Cons: credit-heavy and occasional physics glitches.',
    requiresKey: true,
  },
  {
    value: 'minimax',
    name: 'MiniMax Hailuo 2.3 (fal.ai)',
    description: 'Budget-friendly with smooth, stable motion. Weaker at fast action and lacks native lip sync.',
    requiresKey: true,
  },
  {
    value: 'seedance',
    name: 'Seedance 2.0 (fal.ai)',
    description: 'Strong camera movement and prompt accuracy with native audio. Access is limited and artifacts/text issues remain.',
    requiresKey: true,
  },
];

export function ShortsView({ targetLang, setTargetLang }: ShortsViewProps) {
  const [mode, setMode] = useState<'prompt' | 'script'>('prompt');
  const [videoEngine, setVideoEngine] = useState('local');
  const [prompt, setPrompt] = useState('');
  const [script, setScript] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural');
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const activeText = mode === 'prompt' ? prompt : script;
  const wordCount = activeText.trim().split(/\s+/).filter(Boolean).length;
  const autoEstimatedDuration = Math.max(Math.ceil((wordCount / 150) * 60), 0);
  const [manualDuration, setManualDuration] = useState<number | null>(null);
  const estimatedDuration = manualDuration !== null ? manualDuration : autoEstimatedDuration;

  useEffect(() => {
    api.get('/voices').then((res) => setVoices(res.data)).catch(() => {});
  }, []);

  const filteredVoices = useMemo(() => {
    const matches = voices.filter((voice) => voice.lang === targetLang);
    return matches.length > 0 ? matches : voices;
  }, [voices, targetLang]);

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
      formData.append('text', activeText.substring(0, 200) || 'Quick preview of the selected voice.');
      const response = await api.post('/voice-preview', formData, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setIsPreviewPlaying(false);
      audio.play();
    } catch {
      setError('Failed to preview voice.');
      setIsPreviewPlaying(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim() && !script.trim()) {
      setError('Please provide a prompt or script.');
      return;
    }

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    if (mode === 'prompt') {
      formData.append('prompt', prompt.trim());
    } else {
      formData.append('script', script.trim());
    }
    formData.append('target_lang', targetLang);
    formData.append('voice_id', selectedVoice);
    formData.append('aspect_ratio', '9:16');
    formData.append('video_engine', videoEngine);
    if (manualDuration !== null && manualDuration > 0) {
      formData.append('duration_seconds', String(manualDuration));
    }

    try {
      const response = await api.post('/shorts', formData);
      setJobId(response.data.job_id);
    } catch (err) {
      if (isTimeoutError(err)) {
        setError('Shorts generation timed out, but the worker may still be running.');
      } else {
        setError(extractApiErrorMessage(err, 'Failed to start shorts generation.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const resetShorts = () => {
    setJobId(null);
    setPrompt('');
    setScript('');
    setError(null);
    setManualDuration(null);
    if (audioRef.current) {
      audioRef.current.pause();
    }
  };

  return (
    <>
      {!jobId && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold mb-2">Auto Shorts</h1>
          <p className="text-slate-400 mb-8">
            Caption-first shorts from a prompt or script, tuned for 9:16 platforms.
          </p>
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
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    </div>
                    <p className="text-red-400/80 text-sm">{error}</p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-7 space-y-8">
                  <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
                      <div className="flex items-center justify-between mb-6">
                        <Label className="text-lg font-bold flex items-center gap-2">
                          <span className="bg-emerald-500/20 text-emerald-400 p-1.5 rounded-lg">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                          </span>
                          Content Input
                        </Label>
                        {wordCount > 0 && (
                          <span className="text-xs font-mono bg-emerald-500/10 text-emerald-300 px-3 py-1 rounded-full border border-emerald-500/20">
                            {wordCount} words · ~{estimatedDuration}s
                          </span>
                        )}
                      </div>
                      <Tabs value={mode} onValueChange={(value) => setMode(value as 'prompt' | 'script')}>
                        <TabsList className="mb-4 bg-black/40 border border-white/5 rounded-xl h-12 w-full grid grid-cols-2 p-1">
                          <TabsTrigger value="prompt" className="rounded-lg data-[state=active]:bg-white/10 data-[state=active]:text-emerald-400 transition-all font-semibold">Prompt Mode</TabsTrigger>
                          <TabsTrigger value="script" className="rounded-lg data-[state=active]:bg-white/10 data-[state=active]:text-emerald-400 transition-all font-semibold">Script Mode</TabsTrigger>
                        </TabsList>
                        <TabsContent value="prompt" className="mt-0">
                          <Textarea
                            placeholder="Describe the short you want. We will expand it into a full spoken script..."
                            className="min-h-[250px] bg-black/40 border-white/5 focus:border-emerald-500/50 rounded-xl transition-all resize-none text-base placeholder:text-slate-600 focus:ring-1 focus:ring-emerald-500/50"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                          />
                        </TabsContent>
                        <TabsContent value="script" className="mt-0">
                          <Textarea
                            placeholder="Paste your final script. Keep it concise and conversational..."
                            className="min-h-[250px] bg-black/40 border-white/5 focus:border-emerald-500/50 rounded-xl transition-all resize-none text-base placeholder:text-slate-600 focus:ring-1 focus:ring-emerald-500/50"
                            value={script}
                            onChange={(e) => setScript(e.target.value)}
                          />
                        </TabsContent>
                      </Tabs>
                      <p className="text-xs text-slate-500 mt-4 flex items-center gap-2">
                        <svg className="w-4 h-4 text-emerald-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        Local mode needs no key. Veo/Kling/MiniMax/Seedance require a fal.ai key (FAL_KEY).
                      </p>
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-5 space-y-8">
                  <div className="relative group h-full flex flex-col">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-teal-500/20 to-blue-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl flex-1 flex flex-col">
                      <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <span className="bg-teal-500/20 text-teal-400 p-1.5 rounded-lg">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        </span>
                        Configuration
                      </h3>

                      <div className="space-y-6 flex-1">
                        <div className="space-y-3">
                          <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Video Engine</Label>
                          <div className="space-y-2">
                            {MODEL_OPTIONS.map((option) => {
                              const isSelected = option.value === videoEngine;
                              return (
                                <button
                                  key={option.value}
                                  type="button"
                                  onClick={() => setVideoEngine(option.value)}
                                  className={`w-full text-left rounded-xl border px-4 py-3 transition-all duration-200 ${
                                    isSelected
                                      ? 'border-teal-500/50 bg-teal-500/10 shadow-[0_0_15px_rgba(20,184,166,0.15)] scale-[1.02]'
                                      : 'border-white/5 bg-black/40 hover:border-white/20 hover:bg-black/60'
                                  }`}
                                >
                                  <div className="flex items-center justify-between">
                                    <span className={`text-sm font-bold ${isSelected ? 'text-teal-400' : 'text-slate-200'}`}>{option.name}</span>
                                    {option.requiresKey && (
                                      <span className="text-[10px] font-bold uppercase text-slate-500 bg-white/5 px-2 py-0.5 rounded">FAL_KEY</span>
                                    )}
                                    {!option.requiresKey && (
                                      <span className="text-[10px] font-bold uppercase text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Free</span>
                                    )}
                                  </div>
                                  <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                                    {option.description}
                                  </p>
                                </button>
                              );
                            })}
                          </div>
                        </div>

                        <div className="space-y-3">
                          <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Language</Label>
                          <Select value={targetLang} onValueChange={(value) => {
                            setTargetLang(value);
                            const firstMatch = voices.find((voice) => voice.lang === value);
                            if (firstMatch) {
                              setSelectedVoice(firstMatch.id);
                            }
                          }}>
                            <SelectTrigger className="w-full bg-black/40 border-white/10 hover:border-white/20 transition-colors h-11 rounded-xl">
                              <SelectValue placeholder="Select language" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                              {LANGUAGE_OPTIONS.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                  {option.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-3">
                          <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Voice Model</Label>
                          <div className="flex gap-2">
                            <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                              <SelectTrigger className="flex-1 bg-black/40 border-white/10 hover:border-white/20 transition-colors h-11 rounded-xl">
                                <SelectValue placeholder="Select voice" />
                              </SelectTrigger>
                              <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                                {filteredVoices.map((voice) => (
                                  <SelectItem key={voice.id} value={voice.id}>
                                    <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${voice.gender === 'Female' ? 'bg-pink-500' : 'bg-blue-500'}`}></span>
                                      {voice.name}
                                    </div>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Button
                              variant="outline"
                              className="h-11 w-11 shrink-0 rounded-xl bg-black/40 border-white/10 hover:bg-teal-500/20 hover:border-teal-500/50 hover:text-teal-400 transition-all"
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

                        {wordCount > 0 && (
                          <div className="bg-black/30 rounded-xl p-4 border border-white/5 space-y-3">
                            <div className="flex items-center justify-between">
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Timing</Label>
                              <span className="bg-teal-500/10 text-teal-400 font-mono font-bold px-2 py-0.5 rounded text-sm border border-teal-500/20">
                                {Math.floor(estimatedDuration / 60)}:{String(estimatedDuration % 60).padStart(2, '0')}
                              </span>
                            </div>
                            <div className="flex items-center gap-3">
                              <input
                                type="range"
                                min={8}
                                max={Math.max(90, autoEstimatedDuration * 2)}
                                value={estimatedDuration}
                                onChange={(e) => setManualDuration(Number(e.target.value))}
                                className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-teal-500"
                              />
                              <input
                                type="number"
                                min={8}
                                max={180}
                                value={estimatedDuration}
                                onChange={(e) => setManualDuration(Number(e.target.value) || 0)}
                                className="w-16 bg-black/50 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-center font-mono text-teal-400 focus:border-teal-500/50 outline-none"
                              />
                            </div>
                            {manualDuration !== null && (
                              <div className="text-right">
                                <button
                                  onClick={() => setManualDuration(null)}
                                  className="text-[11px] text-slate-500 hover:text-teal-400 transition-colors font-medium"
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
                          className="w-full btn-glow bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-7 rounded-xl text-lg shadow-[0_0_20px_rgba(20,184,166,0.3)] hover:shadow-[0_0_25px_rgba(20,184,166,0.5)] transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
                          disabled={isLoading}
                          onClick={handleGenerate}
                        >
                          {isLoading ? (
                            <div className="flex items-center justify-center gap-3">
                              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                              <span>Rendering Short...</span>
                            </div>
                          ) : (
                            <span className="flex items-center gap-2">
                              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M19.376 12.416L8.777 19.482A.5.5 0 018 19.066V4.934a.5.5 0 01.777-.416l10.599 7.066a.5.5 0 010 .832z"/></svg>
                              Generate Short
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
                <Button variant="ghost" className="text-slate-400" onClick={resetShorts}>
                  Back to Shorts
                </Button>
                <div className="text-sm text-slate-500">Job ID: <span className="text-slate-300 font-mono">{jobId}</span></div>
              </div>
              <DubbingProgress
                jobId={jobId}
                onComplete={() => console.log('Shorts completed.')}
                onError={(err) => console.error('Shorts failed:', err)}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </>
  );
}
