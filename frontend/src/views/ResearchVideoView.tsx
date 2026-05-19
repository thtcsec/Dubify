import { useState, useEffect, useRef, useMemo } from 'react';
import { Sparkles, Search, ExternalLink, AlertTriangle, Film, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { DubbingProgress } from '@/components/DubbingProgress';
import { StudioOutputSettings } from '@/components/studio/StudioOutputSettings';
import { StudioProjectPreview } from '@/components/studio/StudioProjectPreview';
import api from '@/lib/api';
import { useI18n } from '@/i18n/I18nProvider';
import { isTimeoutError, extractApiErrorMessage } from '@/lib/errors';
import { streamResearchTopic, type ResearchProgressEvent } from '@/lib/researchStream';
import {
  appendStudioBrandToFormData,
  studioBrandStore,
  useDefaultAspectRatio,
  useStudioBrand,
} from '@/lib/studioBrandStore';
import type { AspectRatioValue } from '@/lib/aspectRatios';
import { parseVoicesResponse, type Voice } from '@/lib/voices';

interface ResearchSource {
  title: string;
  url: string;
  snippet: string;
}

interface ResearchVideoViewProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
  onOpenBrandLayout?: () => void;
}

const DEFAULT_TARGET_DURATION = 45;

export function ResearchVideoView({ targetLang, setTargetLang, onOpenBrandLayout }: ResearchVideoViewProps) {
  const { t } = useI18n();
  const [topic, setTopic] = useState('');
  const [script, setScript] = useState('');
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [summary, setSummary] = useState('');
  const [confidence, setConfidence] = useState('');
  const [wikiThumbnailUrl, setWikiThumbnailUrl] = useState('');
  const [verificationIssues, setVerificationIssues] = useState<string[]>([]);
  const [isResearching, setIsResearching] = useState(false);
  const [researchPhase, setResearchPhase] = useState('');
  const [researchStatus, setResearchStatus] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetDuration, setTargetDuration] = useState(DEFAULT_TARGET_DURATION);

  const defaultAspect = useDefaultAspectRatio();
  const { brand, setLayout, socialAvatarPreview } = useStudioBrand();
  const [aspectRatio, setAspectRatio] = useState<AspectRatioValue>(defaultAspect);
  useEffect(() => setAspectRatio(defaultAspect), [defaultAspect]);

  const [studioVisualMode, setStudioVisualMode] = useState<'html_scenes' | 'classic'>('html_scenes');
  const [studioRenderEngine, setStudioRenderEngine] = useState<'auto' | 'playwright' | 'hyperframes'>('auto');
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural');
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api.get('/voices').then((res) => setVoices(parseVoicesResponse(res.data))).catch(() => {});
  }, []);

  const wordCount = script.trim().split(/\s+/).filter(Boolean).length;
  const autoEstimatedDuration = Math.max(Math.ceil(wordCount / 2.4), 0);
  const [manualDuration, setManualDuration] = useState<number | null>(null);
  const estimatedDuration = manualDuration ?? Math.max(autoEstimatedDuration, targetDuration, 30);
  const previewDurationSeconds = estimatedDuration;

  const voiceList = useMemo(() => parseVoicesResponse(voices), [voices]);
  const viVoices = voiceList.filter((v) => v.category === 'vi' || (!v.category && v.lang === 'vi'));
  const enVoices = voiceList.filter((v) => v.category === 'en' || (!v.category && v.lang === 'en'));
  const otherVoices = voiceList.filter((v) => v.category === 'other' || (!v.category && v.lang !== 'vi' && v.lang !== 'en'));

  const phaseLabel = (phase: string) => {
    const map: Record<string, string> = {
      wikipedia: t.researchVideo.phaseWikipedia,
      drafting: t.researchVideo.phaseDrafting,
      parsing: t.researchVideo.phaseParsing,
      writing: t.researchVideo.phaseWriting,
      verify: t.researchVideo.phaseVerify,
      done: t.researchVideo.phaseDone,
    };
    return map[phase] || phase;
  };

  const onResearchEvent = (event: ResearchProgressEvent) => {
    if (event.phase && event.phase !== 'done') {
      setResearchPhase(event.phase);
      setResearchStatus(event.message);
    }
  };

  const handleResearch = async () => {
    if (!topic.trim()) {
      setError(t.researchVideo.needTopic);
      return;
    }
    setIsResearching(true);
    setError(null);
    setResearchPhase('wikipedia');
    setResearchStatus(t.researchVideo.phaseWikipedia);
    setVerificationIssues([]);
    try {
      const result = await streamResearchTopic(topic.trim(), targetLang, onResearchEvent);
      setScript(result.script || '');
      setSources(result.sources || []);
      setSummary(result.research_summary || '');
      setConfidence(result.confidence || 'medium');
      setWikiThumbnailUrl(result.wiki_thumbnail_url || '');
      setVerificationIssues(result.verification_issues || []);
      const suggested = result.suggested_duration_seconds || result.target_duration_seconds || DEFAULT_TARGET_DURATION;
      setTargetDuration(Math.min(60, Math.max(30, suggested)));
    } catch (err) {
      setError(extractApiErrorMessage(err, t.researchVideo.researchFailed));
    } finally {
      setIsResearching(false);
      setResearchPhase('');
      setResearchStatus('');
    }
  };

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
      // Fixed sample text per language — preview is for hearing voice tone, not user content
      const sampleTexts: Record<string, string> = {
        vi: 'Xin chào, đây là giọng đọc mẫu để bạn nghe thử chất lượng âm thanh.',
        en: 'Hello, this is a sample voice preview so you can hear the tone and quality.',
        ja: 'こんにちは、これは音声プレビューのサンプルです。',
        ko: '안녕하세요, 이것은 음성 미리듣기 샘플입니다.',
        zh: '你好，这是一个语音预览示例，让你听听音质。',
        fr: 'Bonjour, ceci est un aperçu vocal pour entendre la qualité.',
        es: 'Hola, esta es una muestra de voz para escuchar la calidad.',
      };
      const previewText = sampleTexts[targetLang] || sampleTexts['vi'];
      formData.append('text', previewText);
      const response = await api.post('/voice-preview', formData, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setIsPreviewPlaying(false);
      audio.play();
    } catch {
      setIsPreviewPlaying(false);
    }
  };

  const handleRender = async () => {
    if (!script.trim()) {
      setError(t.researchVideo.needScript);
      return;
    }
    setIsRendering(true);
    setError(null);
    const formData = new FormData();
    formData.append('text', script);
    formData.append('target_lang', targetLang);
    formData.append('voice_id', selectedVoice);
    formData.append('aspect_ratio', aspectRatio);
    formData.append('use_raw_script', 'false');
    formData.append('research_topic', topic.trim());
    formData.append('project_name', topic.trim().slice(0, 120));
    formData.append('wiki_thumbnail_url', wikiThumbnailUrl);
    formData.append('use_scene_images', 'true');
    if (manualDuration !== null && manualDuration > 0) {
      formData.append('duration_seconds', String(Math.min(90, manualDuration)));
    } else if (wordCount >= 90) {
      formData.append(
        'duration_seconds',
        String(Math.min(90, Math.max(estimatedDuration, targetDuration, 30))),
      );
    }
    formData.append('studio_visual_mode', studioVisualMode);
    formData.append('studio_template', studioBrandStore.getState().studioTemplate);
    formData.append('studio_render_engine', studioRenderEngine);
    appendStudioBrandToFormData(formData);
    try {
      const response = await api.post('/studio', formData);
      setJobId(response.data.job_id);
    } catch (err) {
      setError(isTimeoutError(err) ? t.researchVideo.renderTimeout : extractApiErrorMessage(err, t.researchVideo.renderFailed));
    } finally {
      setIsRendering(false);
    }
  };

  const confidenceColor =
    confidence === 'high' ? 'text-green-400' : confidence === 'low' ? 'text-amber-400' : 'text-cyan-400';

  if (jobId) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" className="text-slate-400" onClick={() => setJobId(null)}>
          ← {t.researchVideo.backToResearch}
        </Button>
        <DubbingProgress jobId={jobId} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold bg-gradient-to-br from-amber-400 to-orange-500 text-transparent bg-clip-text">
            {t.researchVideo.title}
          </h1>
          <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/40 uppercase text-[10px] tracking-wider">
            Beta
          </Badge>
        </div>
        <p className="text-slate-400 max-w-2xl">{t.researchVideo.subtitle}</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-sm text-red-300">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="space-y-4">
          
            <div className="rounded-2xl border border-amber-500/20 bg-slate-900/80 p-5 space-y-4">
              <Label className="text-sm font-semibold flex items-center gap-2">
                <Search className="w-4 h-4 text-amber-400" />
                {t.researchVideo.topicLabel}
              </Label>
              <Textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder={t.researchVideo.topicPlaceholder}
                className="min-h-[100px] bg-black/40 border-white/10"
                disabled={isResearching}
              />
              <Button
                className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500"
                disabled={isResearching}
                onClick={() => void handleResearch()}
              >
                {isResearching ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {phaseLabel(researchPhase)}
                  </span>
                ) : (
                  t.researchVideo.researchBtn
                )}
              </Button>
              {isResearching && researchStatus && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                  <p className="font-semibold uppercase tracking-wide text-amber-300/90">{phaseLabel(researchPhase)}</p>
                  <p className="mt-1 text-slate-200">{researchStatus}</p>
                </div>
              )}
              <p className="text-[11px] text-slate-500">{t.researchVideo.researchHint}</p>
            </div>
          

          {summary && (
            <div className="rounded-xl border border-white/10 bg-black/30 p-4 space-y-2">
              <p className={`text-xs font-semibold uppercase ${confidenceColor}`}>
                {t.researchVideo.confidence}: {confidence}
              </p>
              <p className="text-sm text-slate-300">{summary}</p>
              {confidence === 'low' && (
                <p className="text-[11px] text-amber-400/90 flex items-start gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  {t.researchVideo.lowConfidenceHint}
                </p>
              )}
              {verificationIssues.length > 0 && (
                <ul className="text-[11px] text-slate-400 list-disc pl-4 space-y-0.5">
                  {verificationIssues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {sources.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-2 max-h-[220px] overflow-y-auto">
              <p className="text-xs font-bold uppercase text-slate-500">{t.researchVideo.sourcesTitle}</p>
              {sources.map((s, i) => (
                <div key={`${s.title}-${i}`} className="text-xs border-b border-white/5 pb-2 last:border-0">
                  <p className="font-medium text-slate-200">{s.title}</p>
                  {s.snippet && <p className="text-slate-500 mt-0.5">{s.snippet}</p>}
                  {s.url && (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan-400 hover:underline inline-flex items-center gap-1 mt-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      {t.researchVideo.openSource}
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 space-y-2">
            <Label className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              {t.researchVideo.scriptLabel}
            </Label>
            <Textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              placeholder={t.researchVideo.scriptPlaceholder}
              className="min-h-[200px] bg-black/40 border-white/10 text-sm"
            />
            {wordCount > 0 && (
              <p className="text-[11px] text-slate-500">
                {wordCount} {t.common.words} · ~{estimatedDuration}
                {t.common.seconds} ({t.researchVideo.targetShort})
              </p>
            )}
          </div>
        </div>

        <StudioProjectPreview
          script={script}
          previewDurationSeconds={previewDurationSeconds}
          previewTopic={topic.trim()}
          wikiThumbnailUrl={wikiThumbnailUrl}
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

      <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Film className="w-4 h-4" />
          {t.studio.outputSettings}
        </h3>
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
          autoEstimatedDuration={Math.max(autoEstimatedDuration, targetDuration)}
          manualDuration={manualDuration}
          setManualDuration={setManualDuration}
          isPreviewPlaying={isPreviewPlaying}
          onPreviewVoice={handlePreviewVoice}
        />
        <p className="text-[11px] text-slate-500 leading-snug">{t.researchVideo.renderHint}</p>
        <Button
          className="w-full py-6 font-bold bg-gradient-to-r from-indigo-600 to-purple-600"
          disabled={isRendering || !script.trim()}
          onClick={() => void handleRender()}
        >
          {isRendering ? t.researchVideo.rendering : t.researchVideo.renderBtn}
        </Button>
      </div>
    </div>
  );
}
