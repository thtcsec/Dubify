import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { DubbingProgress } from '../components/DubbingProgress';
import { isTimeoutError, extractApiErrorMessage } from '../lib/errors';
import api from '../lib/api';
import { useI18n } from '@/i18n/I18nProvider';
import { appendStudioBrandToFormData, studioBrandStore, useDefaultAspectRatio, useStudioBrand } from '@/lib/studioBrandStore';
import type { AspectRatioValue } from '@/lib/aspectRatios';
import { parseVoicesResponse, type Voice } from '@/lib/voices';
import { StudioOutputSettings } from '@/components/studio/StudioOutputSettings';
import { StudioProjectPreview } from '@/components/studio/StudioProjectPreview';
import { Wand2, LayoutTemplate } from 'lucide-react';

interface StudioViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
  onOpenBrandLayout?: () => void;
}

export function StudioView({ targetLang, setTargetLang, onOpenBrandLayout }: StudioViewProps) {
  const { t } = useI18n();
  const [jobId, setJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [newsText, setNewsText] = useState('');
  const defaultAspect = useDefaultAspectRatio();
  const { brand, setLayout, socialAvatarPreview } = useStudioBrand();
  const [aspectRatio, setAspectRatio] = useState<AspectRatioValue>(defaultAspect);

  useEffect(() => {
    setAspectRatio(defaultAspect);
  }, [defaultAspect]);
  const [studioVisualMode, setStudioVisualMode] = useState<'html_scenes' | 'classic'>('html_scenes');
  const [studioRenderEngine, setStudioRenderEngine] = useState<'auto' | 'playwright' | 'hyperframes'>('auto');
  const [isRewriting, setIsRewriting] = useState(false);

  // Voice
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural');
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api.get('/voices').then((res) => setVoices(parseVoicesResponse(res.data))).catch(() => {});
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

  const handleGenerate = async () => {
    if (!newsText.trim()) {
        setError(t.studio.needScript);
        return;
    }
    
    setIsLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('text', newsText);
    formData.append('target_lang', targetLang);
    formData.append('voice_id', selectedVoice);
    formData.append('aspect_ratio', aspectRatio);
    formData.append('use_raw_script', 'false');
    if (manualDuration !== null && manualDuration > 0) {
      formData.append('duration_seconds', String(manualDuration));
    }
    formData.append('studio_visual_mode', studioVisualMode);
    formData.append('studio_template', studioBrandStore.getState().studioTemplate);
    formData.append('studio_render_engine', studioRenderEngine);
    appendStudioBrandToFormData(formData);

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

  const handleAiRewrite = async () => {
    if (!newsText.trim()) {
      setError(t.studio.needScript);
      return;
    }
    setIsRewriting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('text', newsText);
      formData.append('target_lang', targetLang);
      const res = await api.post('/studio/rewrite-script', formData);
      setNewsText(res.data.script || newsText);
    } catch (err) {
      setError(extractApiErrorMessage(err, 'AI rewrite failed.'));
    } finally {
      setIsRewriting(false);
    }
  };

  const resetStudio = () => {
    setJobId(null);
    setNewsText('');
    setAspectRatio(defaultAspect);
    setError(null);
    setManualDuration(null);
    setStudioRenderEngine('auto');
    if (audioRef.current) audioRef.current.pause();
  };

  const voiceList = useMemo(() => parseVoicesResponse(voices), [voices]);
  const viVoices = voiceList.filter((v) => v.category === 'vi' || (!v.category && v.lang === 'vi'));
  const enVoices = voiceList.filter((v) => v.category === 'en' || (!v.category && v.lang === 'en'));
  const otherVoices = voiceList.filter((v) => v.category === 'other' || (!v.category && v.lang !== 'vi' && v.lang !== 'en'));
  return (
    <>
      {!jobId && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
           <h1 className="text-3xl font-bold mb-2">{t.studio.title}</h1>
           <p className="text-slate-400 mb-8">{t.studio.subtitle}</p>
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
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                  <div className="relative group min-h-0">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500" />
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-2xl flex flex-col min-h-[420px]">
                      <div className="flex items-center justify-between mb-3 gap-2">
                        <Label className="text-lg font-bold flex items-center gap-2">
                          <span className="bg-indigo-500/20 text-indigo-400 p-1.5 rounded-lg">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                          </span>
                          {t.studio.scriptLabel}
                        </Label>
                        {wordCount > 0 && (
                          <span className="text-xs font-mono bg-indigo-500/10 text-indigo-300 px-2 py-1 rounded-full border border-indigo-500/20 shrink-0">
                            {wordCount} {t.common.words}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2 mb-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="border-purple-500/40 bg-purple-500/10 text-purple-100"
                          disabled={isRewriting || !newsText.trim()}
                          onClick={() => void handleAiRewrite()}
                        >
                          <Wand2 className="w-4 h-4 mr-1" />
                          {isRewriting ? t.studio.aiRewriting : t.studio.aiRewrite}
                        </Button>
                        {onOpenBrandLayout && (
                          <Button type="button" variant="outline" size="sm" onClick={onOpenBrandLayout}>
                            <LayoutTemplate className="w-4 h-4 mr-1" />
                            {t.studio.openBrandLayout}
                          </Button>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 mb-2">{t.studio.aiRewriteHint}</p>
                      <Textarea
                        placeholder={t.studio.scriptPlaceholder}
                        className="flex-1 min-h-[280px] lg:min-h-[340px] bg-black/40 border-white/5 focus:border-indigo-500/50 rounded-xl resize-y text-sm"
                        value={newsText}
                        onChange={(e) => setNewsText(e.target.value)}
                      />
                    </div>
                  </div>

                  <StudioProjectPreview
                    script={newsText}
                    aspectRatio={aspectRatio}
                    template={brand.studioTemplate}
                    layout={brand.layout}
                    onLayoutChange={setLayout}
                    headerEnabled={brand.headerEnabled}
                    headerText={brand.headerText}
                    headerOpacity={brand.headerOpacity}
                    footerEnabled={brand.footerEnabled}
                    footerText={brand.footerText}
                    footerOpacity={brand.footerOpacity}
                    socialOverlay={brand.socialOverlay}
                    socialHandle={brand.socialHandle}
                    socialSubtitle={brand.socialSubtitle}
                    socialAvatarUrl={socialAvatarPreview || undefined}
                    onOpenBrandLayout={onOpenBrandLayout}
                  />
                </div>

                <div className="rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl p-5 shadow-2xl space-y-4">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">{t.studio.outputSettings}</h3>
                  <StudioOutputSettings
                    targetLang={targetLang}
                    setTargetLang={setTargetLang}
                    selectedVoice={selectedVoice}
                    setSelectedVoice={setSelectedVoice}
                    viVoices={viVoices}
                    enVoices={enVoices}
                    otherVoices={otherVoices}
                    voiceList={voiceList}
                    studioVisualMode={studioVisualMode}
                    setStudioVisualMode={setStudioVisualMode}
                    studioRenderEngine={studioRenderEngine}
                    setStudioRenderEngine={setStudioRenderEngine}
                    aspectRatio={aspectRatio}
                    setAspectRatio={setAspectRatio}
                    wordCount={wordCount}
                    estimatedDuration={estimatedDuration}
                    autoEstimatedDuration={autoEstimatedDuration}
                    manualDuration={manualDuration}
                    setManualDuration={setManualDuration}
                    isPreviewPlaying={isPreviewPlaying}
                    onPreviewVoice={handlePreviewVoice}
                  />
                  <Button
                    className="w-full btn-glow bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-6 rounded-xl text-base"
                    disabled={isLoading}
                    onClick={handleGenerate}
                  >
                    {isLoading ? t.studio.generating : t.studio.generate}
                  </Button>
                </div>

            </motion.div>
          ) : (
            <motion.div key="progress" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
               <div className="flex items-center justify-between mb-8">
                  <Button variant="ghost" className="text-slate-400" onClick={resetStudio}>
                    ← {t.studio.backToEditor}
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
