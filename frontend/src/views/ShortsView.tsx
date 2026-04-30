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
                <div className="lg:col-span-8 space-y-6">
                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-3">
                      <Label className="text-base font-semibold">1. Content Input</Label>
                      {wordCount > 0 && (
                        <span className="text-xs text-slate-500">
                          {wordCount} words · ~{estimatedDuration}s
                        </span>
                      )}
                    </div>
                    <Tabs value={mode} onValueChange={(value) => setMode(value as 'prompt' | 'script')}>
                      <TabsList className="mb-4">
                        <TabsTrigger value="prompt">Prompt</TabsTrigger>
                        <TabsTrigger value="script">Script</TabsTrigger>
                      </TabsList>
                      <TabsContent value="prompt">
                        <Textarea
                          placeholder="Describe the short you want. We will expand it into a full spoken script."
                          className="min-h-[200px] bg-slate-950/50 border-slate-800 focus:border-indigo-500 transition-colors"
                          value={prompt}
                          onChange={(e) => setPrompt(e.target.value)}
                        />
                      </TabsContent>
                      <TabsContent value="script">
                        <Textarea
                          placeholder="Paste your final script. Keep it concise and conversational."
                          className="min-h-[200px] bg-slate-950/50 border-slate-800 focus:border-indigo-500 transition-colors"
                          value={script}
                          onChange={(e) => setScript(e.target.value)}
                        />
                      </TabsContent>
                    </Tabs>
                    <p className="text-xs text-slate-500 mt-3">
                      Local mode needs no key. Veo/Kling/MiniMax/Seedance require a fal.ai key (FAL_KEY).
                    </p>
                  </div>
                </div>

                <div className="lg:col-span-4 space-y-6">
                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                      <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                      </svg>
                      Shorts Settings
                    </h3>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label className="text-slate-400 text-xs uppercase tracking-wider">Video Model</Label>
                        <div className="space-y-3">
                          {MODEL_OPTIONS.map((option) => {
                            const isSelected = option.value === videoEngine;
                            return (
                              <button
                                key={option.value}
                                type="button"
                                onClick={() => setVideoEngine(option.value)}
                                className={`w-full text-left rounded-lg border px-3 py-3 transition-colors ${
                                  isSelected
                                    ? 'border-indigo-500/70 bg-indigo-500/10'
                                    : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="text-sm font-semibold text-slate-200">{option.name}</span>
                                  {option.requiresKey && (
                                    <span className="text-[10px] uppercase text-slate-500">FAL_KEY</span>
                                  )}
                                  {!option.requiresKey && (
                                    <span className="text-[10px] uppercase text-emerald-400">Free</span>
                                  )}
                                </div>
                                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                                  {option.description}
                                </p>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-slate-400 text-xs uppercase tracking-wider">Language</Label>
                        <Select value={targetLang} onValueChange={(value) => {
                          setTargetLang(value);
                          const firstMatch = voices.find((voice) => voice.lang === value);
                          if (firstMatch) {
                            setSelectedVoice(firstMatch.id);
                          }
                        }}>
                          <SelectTrigger className="w-full bg-slate-950 border-slate-800">
                            <SelectValue placeholder="Select language" />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-900 border-slate-800">
                            {LANGUAGE_OPTIONS.map((option) => (
                              <SelectItem key={option.value} value={option.value}>
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-slate-400 text-xs uppercase tracking-wider">Voice</Label>
                        <div className="flex gap-2">
                          <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                            <SelectTrigger className="flex-1 bg-slate-950 border-slate-800">
                              <SelectValue placeholder="Select voice" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-900 border-slate-800">
                              {filteredVoices.map((voice) => (
                                <SelectItem key={voice.id} value={voice.id}>
                                  {voice.gender === 'Female' ? 'F' : 'M'} {voice.name} ({voice.lang})
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
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <rect x="6" y="4" width="4" height="16" rx="1" />
                                <rect x="14" y="4" width="4" height="16" rx="1" />
                              </svg>
                            ) : (
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"></path>
                              </svg>
                            )}
                          </Button>
                        </div>
                      </div>

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
                              min={8}
                              max={Math.max(90, autoEstimatedDuration * 2)}
                              value={estimatedDuration}
                              onChange={(e) => setManualDuration(Number(e.target.value))}
                              className="flex-1 accent-indigo-500 h-1.5"
                            />
                            <input
                              type="number"
                              min={8}
                              max={180}
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
                            <span>Rendering Short...</span>
                          </div>
                        ) : (
                          <span className="flex items-center gap-2">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            Generate Short
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
