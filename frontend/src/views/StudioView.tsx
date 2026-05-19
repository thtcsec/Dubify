import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '../components/ui/select';
import { DubbingProgress } from '../components/DubbingProgress';
import { isTimeoutError, extractApiErrorMessage } from '../lib/errors';
import api from '../lib/api';
import { useI18n } from '@/i18n/I18nProvider';
import { appendStudioBrandToFormData, studioBrandStore, useDefaultAspectRatio, useStudioBrand } from '@/lib/studioBrandStore';
import { ASPECT_RATIO_OPTIONS, type AspectRatioValue } from '@/lib/aspectRatios';
import { parseVoicesResponse, type Voice } from '@/lib/voices';
import { StudioLayoutPreview } from '@/components/studio/StudioLayoutPreview';
import { Wand2, LayoutTemplate, Eye } from 'lucide-react';

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
    formData.append('use_raw_script', 'true');
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
  const aspectLabel = (value: string) => {
    const key = value.replace(':', '_') as '16_9' | '9_16' | '4_3' | '3_4' | '1_1';
    return t.brandLayout.ratios[key] ?? value;
  };

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
                          {t.studio.scriptLabel}
                        </Label>
                        {wordCount > 0 && (
                          <span className="text-xs font-mono bg-indigo-500/10 text-indigo-300 px-3 py-1 rounded-full border border-indigo-500/20">
                            {wordCount} {t.common.words} · ~{estimatedDuration}{t.common.seconds}
                          </span>
                        )}
                      </div>
                      <motion.div className="flex flex-wrap gap-2 mb-3">
                        <Button
                          type="button"
                          variant="outline"
                          className="border-purple-500/40 bg-purple-500/10 text-purple-100"
                          disabled={isRewriting || !newsText.trim()}
                          onClick={() => void handleAiRewrite()}
                        >
                          <Wand2 className="w-4 h-4 mr-2" />
                          {isRewriting ? t.studio.aiRewriting : t.studio.aiRewrite}
                        </Button>
                        {onOpenBrandLayout && (
                          <Button type="button" variant="outline" onClick={onOpenBrandLayout}>
                            <LayoutTemplate className="w-4 h-4 mr-2" />
                            {t.studio.openBrandLayout}
                          </Button>
                        )}
                      </motion.div>
                      <p className="text-[11px] text-slate-500 mb-3">{t.studio.aiRewriteHint}</p>
                      <Textarea 
                        placeholder={t.studio.scriptPlaceholder}
                        className="min-h-[180px] bg-black/40 border-white/5 focus:border-indigo-500/50 rounded-xl transition-all resize-none text-base placeholder:text-slate-600 focus:ring-1 focus:ring-indigo-500/50"
                        value={newsText}
                        onChange={(e) => setNewsText(e.target.value)}
                      />
                    </div>
                  </div>


                </div>
                <div className="lg:col-span-5 space-y-6">
                  <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500/20 to-indigo-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500" />
                    <div className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-2xl space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <Label className="text-lg font-bold flex items-center gap-2">
                          <span className="bg-cyan-500/20 text-cyan-400 p-1.5 rounded-lg">
                            <Eye className="w-5 h-5" />
                          </span>
                          {t.studio.projectPreviewTitle}
                        </Label>
                        {onOpenBrandLayout && (
                          <Button type="button" variant="ghost" size="sm" className="text-cyan-300 h-8" onClick={onOpenBrandLayout}>
                            <LayoutTemplate className="w-3.5 h-3.5 mr-1" />
                            {t.studio.openBrandLayout}
                          </Button>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 leading-snug">{t.studio.projectPreviewHint}</p>
                      {newsText.trim() ? (
                        <StudioLayoutPreview
                          script={newsText}
                          imagePreview=""
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
                        />
                      ) : (
                        <p className="text-xs text-slate-500 text-center py-12 border border-dashed border-white/10 rounded-xl">
                          {t.studio.projectPreviewEmpty}
                        </p>
                      )}
                    </div>
                  </div>

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
                                const pool = v === 'en' ? enVoices : v === 'vi' ? viVoices : voiceList;
                                const firstMatch = pool[0] ?? voiceList.find((voice) => voice.lang === v);
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
                                <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl max-h-72">
                                    {viVoices.length > 0 && (
                                      <SelectGroup>
                                        <SelectLabel className="text-cyan-400/90 text-xs uppercase tracking-wider">Tiếng Việt</SelectLabel>
                                        {viVoices.map((v) => (
                                          <SelectItem key={v.id} value={v.id}>
                                            <div className="flex flex-col gap-0.5">
                                              <span className="flex items-center gap-2">
                                                <span className={`w-2 h-2 rounded-full ${v.gender === 'Female' ? 'bg-pink-500' : 'bg-blue-500'}`} />
                                                {v.name}
                                                {v.accent && <span className="text-[10px] text-slate-500">{v.accent}</span>}
                                              </span>
                                              {v.style && <span className="text-[10px] text-slate-500 pl-4">{v.style}</span>}
                                            </div>
                                          </SelectItem>
                                        ))}
                                      </SelectGroup>
                                    )}
                                    {enVoices.length > 0 && (
                                      <SelectGroup>
                                        <SelectLabel className="text-violet-400/90 text-xs uppercase tracking-wider">English</SelectLabel>
                                        {enVoices.map((v) => (
                                          <SelectItem key={v.id} value={v.id}>
                                            <div className="flex flex-col gap-0.5">
                                              <span className="flex items-center gap-2">
                                                <span className={`w-2 h-2 rounded-full ${v.gender === 'Female' ? 'bg-pink-500' : 'bg-blue-500'}`} />
                                                {v.name}
                                                {v.accent && <span className="text-[10px] text-slate-500">{v.accent}</span>}
                                              </span>
                                              {v.style && <span className="text-[10px] text-slate-500 pl-4">{v.style}</span>}
                                            </div>
                                          </SelectItem>
                                        ))}
                                      </SelectGroup>
                                    )}
                                    {otherVoices.length > 0 && (
                                      <SelectGroup>
                                        <SelectLabel className="text-slate-500 text-xs uppercase tracking-wider">Khác</SelectLabel>
                                        {otherVoices.map((v) => (
                                          <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>
                                        ))}
                                      </SelectGroup>
                                    )}
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
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">{t.studio.visualMode}</Label>
                              <Select value={studioVisualMode} onValueChange={(v) => setStudioVisualMode(v as 'html_scenes' | 'classic')}>
                                <SelectTrigger className="w-full bg-black/40 border-white/10 h-11 rounded-xl">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-900 border-white/10 rounded-xl">
                                  <SelectItem value="html_scenes">{t.studio.modeHtmlScenes}</SelectItem>
                                  <SelectItem value="classic">{t.studio.modeClassic}</SelectItem>
                                </SelectContent>
                              </Select>
                              <p className="text-[11px] text-slate-500 leading-snug">{t.studio.sectionHint}</p>
                          </div>

                          {studioVisualMode === 'html_scenes' && (
                          <motion.div className="space-y-2.5">
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">{t.studio.renderEngine}</Label>
                              <Select value={studioRenderEngine} onValueChange={(v) => setStudioRenderEngine(v as 'auto' | 'playwright' | 'hyperframes')}>
                                <SelectTrigger className="w-full bg-black/40 border-white/10 h-11 rounded-xl">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-900 border-white/10 rounded-xl">
                                  <SelectItem value="auto">{t.studio.renderAuto}</SelectItem>
                                  <SelectItem value="hyperframes">{t.studio.renderHyperframes}</SelectItem>
                                  <SelectItem value="playwright">{t.studio.renderPlaywright}</SelectItem>
                                </SelectContent>
                              </Select>
                              <p className="text-[11px] text-slate-500 leading-snug">{t.studio.renderEngineHint}</p>
                          </motion.div>
                          )}

                          {onOpenBrandLayout && (
                            <button
                              type="button"
                              onClick={onOpenBrandLayout}
                              className="w-full rounded-xl border border-dashed border-cyan-500/30 bg-cyan-500/5 px-4 py-3 text-left hover:bg-cyan-500/10 transition-colors"
                            >
                              <p className="text-sm font-medium text-cyan-100">{t.studio.openBrandLayout}</p>
                              <p className="text-[11px] text-slate-500 mt-1">{t.brandLayout.sharedHint}</p>
                            </button>
                          )}

                          <div className="space-y-2.5">
                              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">Canvas Format</Label>
                              <Select value={aspectRatio} onValueChange={(v) => setAspectRatio(v as AspectRatioValue)}>
                                <SelectTrigger className="w-full bg-black/40 border-white/10 hover:border-white/20 transition-colors h-11 rounded-xl">
                                  <SelectValue placeholder="Select aspect ratio" />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                                  {ASPECT_RATIO_OPTIONS.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                      {aspectLabel(option.value)}
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
