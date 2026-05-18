import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { VideoSourceSection } from '@/components/dashboard/VideoSourceSection';
import { DubbingProgress } from '../components/DubbingProgress';
import { isTimeoutError, extractApiErrorMessage } from '../lib/errors';
import api, { uploadApi } from '../lib/api';
import { useI18n } from '@/i18n/I18nProvider';
import { parseVoicesResponse, type Voice } from '@/lib/voices';

const LANGUAGE_OPTIONS = [
  { value: 'vi', label: 'Vietnamese' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'zh', label: 'Chinese' },
];

interface ShortsViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
}

interface VideoInfo {
  title: string;
  duration: number;
  thumbnail?: string | null;
  source?: string | null;
}

export function ShortsView({ targetLang, setTargetLang }: ShortsViewProps) {
  const { t } = useI18n();
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [maxPartDuration, setMaxPartDuration] = useState(60);
  const [verticalCrop, setVerticalCrop] = useState(true);

  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural');

  useEffect(() => {
    api.get('/voices').then((res) => setVoices(parseVoicesResponse(res.data))).catch(() => {});
  }, []);

  const voiceList = useMemo(() => parseVoicesResponse(voices), [voices]);
  const filteredVoices = useMemo(() => {
    const matches = voiceList.filter((v) => v.lang === targetLang);
    return matches.length > 0 ? matches : voiceList;
  }, [voiceList, targetLang]);

  const estimatedParts = useMemo(() => {
    if (!videoInfo?.duration) return null;
    return Math.max(1, Math.ceil(videoInfo.duration / maxPartDuration));
  }, [videoInfo?.duration, maxPartDuration]);

  const handleFetchInfo = async () => {
    if (!videoUrl.trim()) return;
    setIsLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('url', videoUrl.trim());
    try {
      const res = await api.post('/fetch-info', formData);
      setVideoInfo(res.data);
    } catch (err) {
      setError(extractApiErrorMessage(err, t.dashboard.fetchInvalid));
      setVideoInfo(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!file && !videoUrl.trim()) {
      setError(t.shorts.needVideo);
      return;
    }
    setIsLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('target_lang', targetLang);
    formData.append('voice_id', selectedVoice);
    formData.append('max_part_duration', String(maxPartDuration));
    formData.append('vertical_crop', verticalCrop ? 'true' : 'false');
    if (file) {
      formData.append('file', file);
    } else {
      formData.append('video_url', videoUrl.trim());
    }
    try {
      const client = file ? uploadApi : api;
      const res = await client.post('/shorts', formData);
      setJobId(res.data.job_id);
    } catch (err) {
      setError(
        isTimeoutError(err)
          ? t.shorts.timeout
          : extractApiErrorMessage(err, t.shorts.failed),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const resetShorts = () => {
    setJobId(null);
    setFile(null);
    setVideoUrl('');
    setVideoInfo(null);
    setError(null);
  };

  return (
    <>
      {!jobId && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold mb-2">{t.shorts.title}</h1>
          <p className="text-slate-400 mb-8">{t.shorts.subtitle}</p>
        </motion.div>
      )}

      <main>
        <AnimatePresence mode="wait">
          {!jobId ? (
            <motion.div key="creation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-400/90 text-sm">{error}</div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-7">
                  <VideoSourceSection
                    file={file}
                    setFile={setFile}
                    videoUrl={videoUrl}
                    setVideoUrl={setVideoUrl}
                    videoInfo={videoInfo}
                    isLoading={isLoading}
                    onFetchInfo={handleFetchInfo}
                  />
                  <p className="text-xs text-slate-500 mt-3 leading-relaxed">{t.shorts.flowHint}</p>
                </div>

                <motion.div className="lg:col-span-5 space-y-6">
                  <div className="bg-slate-900/80 border border-white/10 rounded-2xl p-6 space-y-6">
                    <h3 className="text-lg font-bold text-slate-100">{t.shorts.configTitle}</h3>

                    <div className="space-y-2">
                      <div className="flex justify-between text-xs text-slate-400">
                        <Label>{t.shorts.maxPartDuration}</Label>
                        <span className="font-mono text-emerald-300">{maxPartDuration}s</span>
                      </div>
                      <input
                        type="range"
                        min={30}
                        max={90}
                        value={maxPartDuration}
                        onChange={(e) => setMaxPartDuration(Number(e.target.value))}
                        className="w-full accent-emerald-500"
                      />
                      {estimatedParts != null && (
                        <p className="text-xs text-emerald-400/90 font-mono">
                          {t.shorts.estimatedParts}: ~{estimatedParts} {t.shorts.parts}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-black/30 px-4 py-3">
                      <div>
                        <p className="text-sm text-slate-200">{t.shorts.verticalCrop}</p>
                        <p className="text-xs text-slate-500">{t.shorts.verticalCropHint}</p>
                      </div>
                      <Switch checked={verticalCrop} onCheckedChange={setVerticalCrop} />
                    </div>

                    <div className="space-y-3">
                      <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Language</Label>
                      <Select
                        value={targetLang}
                        onValueChange={(v) => {
                          setTargetLang(v);
                          const match = voiceList.find((voice) => voice.lang === v);
                          if (match) setSelectedVoice(match.id);
                        }}
                      >
                        <SelectTrigger className="bg-black/40 border-white/10 h-11 rounded-xl">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-white/10">
                          {LANGUAGE_OPTIONS.map((o) => (
                            <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-3">
                      <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Voice</Label>
                      <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                        <SelectTrigger className="bg-black/40 border-white/10 h-11 rounded-xl">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-white/10 max-h-72">
                          {filteredVoices.map((v) => (
                            <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <Button
                      className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-7 rounded-xl"
                      disabled={isLoading}
                      onClick={handleGenerate}
                    >
                      {isLoading ? t.shorts.starting : t.shorts.generate}
                    </Button>
                  </div>
                </motion.div>
              </div>
            </motion.div>
          ) : (
            <motion.div key="progress" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
              <div className="flex items-center justify-between mb-8">
                <Button variant="ghost" className="text-slate-400" onClick={resetShorts}>
                  {t.shorts.back}
                </Button>
                <span className="text-sm text-slate-500 font-mono">{jobId}</span>
              </div>
              <DubbingProgress jobId={jobId} onError={setError} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </>
  );
}
