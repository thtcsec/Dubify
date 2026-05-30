import { useState, useEffect, useRef, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Sparkles, Search, ExternalLink, AlertTriangle, Film, Loader2, CheckCircle2, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { DubbingProgress } from '@/components/DubbingProgress';
import { StudioOutputSettings } from '@/components/studio/StudioOutputSettings';
import { StudioProjectPreview, type SceneReviewCard } from '@/components/studio/StudioProjectPreview';
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
import { parseStudioScenes } from '@/lib/studioScenes';

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
type WizardStep = 1 | 2 | 3 | 4;
type DemoScenarioKey = 'marketing' | 'gaming' | 'film';

const HACKATHON_DEMO_TOPIC =
  'vivo X300 Ultra launch campaign for Southeast Asia creators: focus on dual 200MP cameras, cinematic mobile filmmaking, pro-grade zoom, and creator-first video workflow.';

const HACKATHON_DEMO_SCRIPT = `[Scene 1]
vivo X300 Ultra is not just another flagship phone. It is being positioned as a creator-first camera system built for cinematic mobile storytelling.

[Scene 2]
Its dual 200MP camera setup pushes the product into a different tier, combining high-detail capture with professional-style zoom and a more serious imaging identity.

[Scene 3]
For creators, the value is not only hardware. It is the speed of turning one idea into a polished campaign asset that looks premium on short-form platforms.

[Scene 4]
That is where Dubify and PixVerse work together. PixVerse generates the visual beats, and Dubify handles workflow, voice, subtitles, and final assembly.

[Scene 5]
The result is a faster path from product story to campaign-ready video, with human review still in the loop before export.`;

const HACKATHON_DEMO_SCENES: SceneReviewCard[] = [
  {
    id: 'scene_1',
    title: 'Scene 1',
    text: 'vivo X300 Ultra is not just another flagship phone. It is being positioned as a creator-first camera system built for cinematic mobile storytelling.',
    prompt:
      'Subject: vivo X300 Ultra hero device on a premium dark stage. Action: dramatic reveal with light streaks and floating lens reflections. Camera movement: slow push in and subtle orbit. Lighting and style: PixVerse V6, cinematic product commercial, ultra detailed, premium contrast, luxury tech launch. Context: flagship smartphone opening hero shot for Southeast Asia creator campaign.',
    durationSeconds: 6,
    approved: true,
    forceFallback: false,
    status: 'kept',
  },
  {
    id: 'scene_2',
    title: 'Scene 2',
    text: 'Its dual 200MP camera setup pushes the product into a different tier, combining high-detail capture with professional-style zoom and a more serious imaging identity.',
    prompt:
      'Subject: close-up of vivo X300 Ultra circular camera ring module with dual 200MP storytelling emphasis. Action: macro camera module reveal with precision highlights and glass reflections, round camera ring clearly visible. Camera movement: slow macro slide and tilt. Lighting and style: PixVerse V6, cinematic macro commercial, sharp metal texture, glossy premium look. Context: emphasize creator-grade camera identity.',
    durationSeconds: 6,
    approved: true,
    forceFallback: false,
    status: 'kept',
  },
  {
    id: 'scene_3',
    title: 'Scene 3',
    text: 'For creators, the value is not only hardware. It is the speed of turning one idea into a polished campaign asset that looks premium on short-form platforms.',
    prompt:
      'Subject: young creator filming with vivo X300 Ultra in an urban night setting. Action: switching from capture to editing mindset, confident creator energy. Camera movement: handheld cinematic drift. Lighting and style: PixVerse V6, social-first premium ad, neon city bokeh, realistic cinematic motion. Context: mobile creator workflow and content production.',
    durationSeconds: 6,
    approved: true,
    forceFallback: false,
    status: 'kept',
  },
  {
    id: 'scene_4',
    title: 'Scene 4',
    text: 'That is where Dubify and PixVerse work together. PixVerse generates the visual beats, and Dubify handles workflow, voice, subtitles, and final assembly.',
    prompt:
      'Subject: city skyline and portrait subject captured through long-range mobile zoom. Action: smooth zoom storytelling with stable focus and premium lens feel. Camera movement: slow zoom and lateral drift. Lighting and style: PixVerse V6, cinematic telephoto look, polished ad aesthetic, realistic depth compression. Context: show pro-grade zoom and storytelling power.',
    durationSeconds: 6,
    approved: true,
    forceFallback: false,
    status: 'kept',
  },
  {
    id: 'scene_5',
    title: 'Scene 5',
    text: 'The result is a faster path from product story to campaign-ready video, with human review still in the loop before export.',
    prompt:
      'Subject: vivo X300 Ultra centered with bold title card and campaign finish. Action: product rotates slightly while logo and creator message resolve on screen. Camera movement: smooth orbit and settle. Lighting and style: PixVerse V6, premium launch finale, high-contrast cinematic lighting, luxury smartphone ad. Context: final campaign-ready call to action.',
    durationSeconds: 6,
    approved: true,
    forceFallback: false,
    status: 'kept',
  },
];

const shellTransition = { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const };
const fadeUpVariants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0 },
};
const staggerVariants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.04,
    },
  },
};

function estimateSceneDuration(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  // Guide says 5-8s per shot. Let's aim for 7s average to hit 30s+ easily.
  return Math.max(6, Math.min(8, Math.round(words / 6) || 7));
}

function buildPixVersePrompt(title: string, text: string, topic: string): string {
  const normalized = `${title} ${text}`.replace(/\s+/g, ' ').trim();
  const words = normalized.split(' ').filter(Boolean);
  const subject = words.slice(0, 6).join(' ') || topic || 'main subject';
  const action = words.slice(6, 20).join(' ') || normalized || 'dynamic cinematic motion';
  const style = `PixVerse V6, cinematic 4k, highly detailed, professional lighting, social media viral style, themed around ${topic || 'innovation'}`;
  const productHint = (topic || '').toLowerCase().includes('x300 ultra')
    ? ' Include vivo X300 Ultra with a circular camera ring module.'
    : '';
  
  return `Subject: ${subject}. Action: ${action}. Camera movement: slow push in and orbit. Lighting and style: ${style}.${productHint} Context: ${normalized || topic || 'visual storytelling beat'}.`;
}

function splitSceneText(text: string): [string, string] {
  const cleaned = text.replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return ['Main visual beat.', 'Supporting visual beat.'];
  }
  const sentences = cleaned
    .replace(/[!?]/g, '.')
    .split('.')
    .map((part) => part.trim())
    .filter(Boolean);
  if (sentences.length >= 2) {
    const middle = Math.max(1, Math.floor(sentences.length / 2));
    return [`${sentences.slice(0, middle).join('. ')}.`, `${sentences.slice(middle).join('. ')}.`];
  }
  const words = cleaned.split(' ');
  const middle = Math.max(1, Math.floor(words.length / 2));
  return [words.slice(0, middle).join(' '), words.slice(middle).join(' ') || cleaned];
}

function normalizeSceneReviewCards(script: string, topic: string): SceneReviewCard[] {
  let cards: SceneReviewCard[] = parseStudioScenes(script).map((scene, index) => ({
    id: `scene_${index + 1}`,
    title: scene.title || `Scene ${index + 1}`,
    text: scene.body || scene.title || '',
    prompt: buildPixVersePrompt(scene.title || `Scene ${index + 1}`, scene.body || scene.title || '', topic),
    durationSeconds: estimateSceneDuration(scene.body || scene.title || ''),
    approved: true,
    forceFallback: false,
    status: 'draft' as const,
  }));

  // Force at least 5 scenes if possible to hit 30s+ safely with 6-7s shots
  while (cards.length > 0 && cards.length < 5) {
    let splitIndex = 0;
    let longest = 0;
    cards.forEach((card, index) => {
      const size = card.text.length;
      if (size > longest) {
        longest = size;
        splitIndex = index;
      }
    });
    const target = cards[splitIndex];
    const [leftText, rightText] = splitSceneText(target.text);
    const replacements: SceneReviewCard[] = [
      {
        ...target,
        id: `${target.id}_a`,
        title: `${target.title} A`,
        text: leftText,
        prompt: buildPixVersePrompt(`${target.title} A`, leftText, topic),
        durationSeconds: estimateSceneDuration(leftText),
      },
      {
        ...target,
        id: `${target.id}_b`,
        title: `${target.title} B`,
        text: rightText,
        prompt: buildPixVersePrompt(`${target.title} B`, rightText, topic),
        durationSeconds: estimateSceneDuration(rightText),
      },
    ];
    cards = [...cards.slice(0, splitIndex), ...replacements, ...cards.slice(splitIndex + 1)];
  }

  // Ensure total duration is at least 30s by padding last scene if needed
  const totalDur = cards.reduce((sum, c) => sum + c.durationSeconds, 0);
  if (totalDur < 30 && cards.length > 0) {
    const last = cards[cards.length - 1];
    last.durationSeconds += (30 - totalDur);
  }

  if (cards.length > 8) {
    const head = cards.slice(0, 7);
    const tail = cards.slice(7);
    const mergedText = tail.map((card) => card.text).join(' ').trim();
    head.push({
      id: 'scene_merged_tail',
      title: 'Final Scene',
      text: mergedText,
      prompt: buildPixVersePrompt('Final Scene', mergedText, topic),
      durationSeconds: estimateSceneDuration(mergedText),
      approved: true,
      forceFallback: false,
      status: 'draft',
    });
    cards = head;
  }

  return cards.map((card, index) => ({
    ...card,
    id: `scene_${index + 1}`,
    title: card.title || `Scene ${index + 1}`,
  }));
}

function pickDemoVoice(voices: Voice[], fallback: string): string {
  const englishPriority =
    voices.find((voice) => voice.id.startsWith('elevenlabs:') && voice.lang.startsWith('en')) ||
    voices.find((voice) => voice.lang.startsWith('en') && /news|narrat|studio|professional|ava|andrew/i.test(`${voice.name} ${voice.style || ''}`)) ||
    voices.find((voice) => voice.lang.startsWith('en'));
  return englishPriority?.id || fallback;
}

export function ResearchVideoView({ targetLang, setTargetLang, onOpenBrandLayout }: ResearchVideoViewProps) {
  const { t } = useI18n();
  const [topic, setTopic] = useState('');
  const [script, setScript] = useState('');
  const [wizardStep, setWizardStep] = useState<WizardStep>(1);
  const [sceneReviewCards, setSceneReviewCards] = useState<SceneReviewCard[]>([]);
  const [sceneClipFiles, setSceneClipFiles] = useState<Record<string, File | null>>({});
  const [usePixverseClipFolder, setUsePixverseClipFolder] = useState(false);
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
      setSceneReviewCards([]);
      setSceneClipFiles({});
      setWizardStep(2);
    } catch (err) {
      setError(extractApiErrorMessage(err, t.researchVideo.researchFailed));
    } finally {
      setIsResearching(false);
      setResearchPhase('');
      setResearchStatus('');
    }
  };

  const handleHackathonDemo = () => {
    setTargetLang('en');
    setTopic(HACKATHON_DEMO_TOPIC);
    setScript(HACKATHON_DEMO_SCRIPT);
    setSelectedVoice(pickDemoVoice(voiceList, selectedVoice));
    setAspectRatio('9:16');
    setUsePixverseClipFolder(true);
    setSources([]);
    setSummary(
      'Creator-first flagship marketing demo with a PixVerse shot plan, English narration, and a 30-second campaign-ready export path.'
    );
    setConfidence('high');
    setWikiThumbnailUrl('');
    setVerificationIssues([]);
    setTargetDuration(45);
    setManualDuration(null);
    setSceneReviewCards(HACKATHON_DEMO_SCENES);
    setSceneClipFiles({});
    setWizardStep(3);
    setError(null);
  };

  const loadDemoScenario = (key: DemoScenarioKey) => {
    const scenarios: Record<DemoScenarioKey, { topic: string; script: string }> = {
      marketing: {
        topic: 'AI Phone 2026 Launch — preorder campaign',
        script:
          'Cảnh 1:\n' +
          'Đây là chiếc AI Phone 2026 — điện thoại biết dự đoán bạn cần gì trước khi bạn chạm.\n' +
          '[STAT: 3 giây — Thời gian để AI Phone dựng kế hoạch ngày mới]\n\n' +
          'Cảnh 2:\n' +
          'Từ camera đến lịch, mọi app trở thành một trải nghiệm liền mạch.\n' +
          '[DEF: AI Phone — Smartphone có agent chạy xuyên suốt hệ điều hành]\n\n' +
          'Cảnh 3:\n' +
          'Bạn chọn: “Đi công tác 2 ngày”. Máy tự đặt lịch, sắp vali, tối ưu pin và mạng.\n' +
          '[STAT: 30% — Mức tiết kiệm thời gian mỗi ngày]\n\n' +
          'Cảnh 4:\n' +
          'Và quan trọng nhất: quyền riêng tư. Mọi xử lý nhạy cảm chạy on-device.\n' +
          '[STAT: 0 — Dữ liệu cá nhân rời khỏi máy]\n\n' +
          'Cảnh 5:\n' +
          'CTA: Đặt trước hôm nay — nhận gói “AI Concierge” 12 tháng.\n',
      },
      gaming: {
        topic: 'Gaming — character reveal trailer',
        script:
          'Cảnh 1:\n' +
          'Thành phố Neon 2096. Một nhân vật xuất hiện: “Cipher”.\n' +
          '[STAT: 8 giây — Thời gian để hacker phá một cánh cổng an ninh]\n\n' +
          'Cảnh 2:\n' +
          'Cipher lao qua hành lang ánh đèn, camera orbit, mưa và phản xạ neon.\n' +
          '[DEF: Cipher Mode — Kỹ năng làm chậm thời gian 0.5x]\n\n' +
          'Cảnh 3:\n' +
          'Boss reveal: drone khổng lồ, tia laser quét ngang, rung màn.\n' +
          '[STAT: 1% — Cơ hội sống sót nếu đứng yên]\n\n' +
          'Cảnh 4:\n' +
          'Twist: Cipher không chạy trốn — Cipher hack chính ánh sáng.\n' +
          '[STAT: 60 FPS — Nhịp combat]\n\n' +
          'Cảnh 5:\n' +
          'CTA: Vote phong cách trailer bạn muốn: “Noir” hay “Neon Pop”.\n',
      },
      film: {
        topic: 'Film — pitch teaser with scene breakdown',
        script:
          'Cảnh 1:\n' +
          'Mở đầu: một căn phòng trắng, đồng hồ chạy ngược.\n' +
          '[DEF: Reverse Clock — Đồng hồ đếm ngược ký ức]\n\n' +
          'Cảnh 2:\n' +
          'Nhân vật chính nhìn thấy tương lai qua các mảnh ký ức vỡ.\n' +
          '[STAT: 7 cảnh — Số mảnh ký ức mỗi lần “flash”]\n\n' +
          'Cảnh 3:\n' +
          'Cú máy: handheld, cận mặt, hơi thở gấp, ánh sáng lạnh.\n' +
          '[STAT: 1 lựa chọn — Đổi tương lai]\n\n' +
          'Cảnh 4:\n' +
          'Cao trào: ký ức và hiện tại chồng lên nhau như 2 lớp phim.\n' +
          '[STAT: 30 giây — Teaser đủ để pitch]\n\n' +
          'Cảnh 5:\n' +
          'CTA: Chọn ending: “Save them” hay “Save yourself”.\n',
      },
    };

    const selected = scenarios[key];
    setTopic(selected.topic);
    setScript(selected.script);
    setSources([]);
    setSummary('');
    setConfidence('high');
    setWikiThumbnailUrl('');
    setVerificationIssues([]);
    setTargetDuration(DEFAULT_TARGET_DURATION);
    setSceneReviewCards(normalizeSceneReviewCards(selected.script, selected.topic));
    setSceneClipFiles({});
    setWizardStep(3);
    setError(null);
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
    if (!sceneReviewCards.length) {
      setError(t.researchVideo.needSceneReview);
      return;
    }
    const selectedClips = sceneReviewCards.filter((scene) => Boolean(sceneClipFiles[scene.id])).length;
    if (!usePixverseClipFolder && selectedClips > 0 && selectedClips !== sceneReviewCards.length) {
      setError(t.researchVideo.needAllPixverseClips);
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
    if (usePixverseClipFolder) {
      formData.append('pixverse_clip_dir', 'pixverse_smoke');
    } else if (selectedClips === sceneReviewCards.length) {
      sceneReviewCards.forEach((scene) => {
        const file = sceneClipFiles[scene.id];
        if (file) formData.append('pixverse_clips', file, file.name);
      });
    }
    formData.append(
      'scene_review_json',
      JSON.stringify(
        sceneReviewCards.map((scene) => ({
          sceneId: scene.id,
          title: scene.title,
          description: scene.text,
          prompt: scene.prompt,
          approved: scene.approved,
          forceFallback: scene.forceFallback,
          durationSeconds: scene.durationSeconds,
        })),
      ),
    );
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
  const steps = [
    { id: 1 as const, label: t.researchVideo.stepTopic },
    { id: 2 as const, label: t.researchVideo.stepScript },
    { id: 3 as const, label: t.researchVideo.stepScenes },
    { id: 4 as const, label: t.researchVideo.stepRender },
  ];

  const handleApproveScript = () => {
    if (!script.trim()) {
      setError(t.researchVideo.needScript);
      return;
    }
    setSceneReviewCards(normalizeSceneReviewCards(script, topic.trim()));
    setSceneClipFiles({});
    setError(null);
    setWizardStep(3);
  };

  const handleScenePromptChange = (sceneId: string, prompt: string) => {
    setSceneReviewCards((current) =>
      current.map((scene) =>
        scene.id === sceneId ? { ...scene, prompt, approved: true, status: 'draft' } : scene,
      ),
    );
  };

  const handleSceneKeep = (sceneId: string) => {
    setSceneReviewCards((current) =>
      current.map((scene) =>
        scene.id === sceneId ? { ...scene, approved: true, forceFallback: false, status: 'kept' } : scene,
      ),
    );
  };

  const handleSceneRegenerate = (sceneId: string) => {
    setSceneReviewCards((current) =>
      current.map((scene) =>
        scene.id === sceneId
          ? {
              ...scene,
              prompt: buildPixVersePrompt(scene.title, scene.text, topic.trim()),
              approved: true,
              forceFallback: false,
              status: 'regenerated',
            }
          : scene,
      ),
    );
  };

  const handleSceneFallback = (sceneId: string) => {
    setSceneReviewCards((current) =>
      current.map((scene) =>
        scene.id === sceneId
          ? {
              ...scene,
              approved: true,
              forceFallback: !scene.forceFallback,
              status: !scene.forceFallback ? 'fallback' : 'kept',
            }
          : scene,
      ),
    );
  };

  const handleSceneClipSelect = (sceneId: string, file: File | null) => {
    setSceneClipFiles((current) => ({ ...current, [sceneId]: file }));
    setSceneReviewCards((current) =>
      current.map((scene) => (scene.id === sceneId ? { ...scene, clipName: file?.name } : scene)),
    );
  };

  const handleContinueToRender = () => {
    if (!sceneReviewCards.length) {
      setError(t.researchVideo.needSceneReview);
      return;
    }
    setError(null);
    setWizardStep(4);
  };

  if (jobId) {
    return (
      <motion.div initial="hidden" animate="show" variants={staggerVariants} className="space-y-6">
        <Button variant="ghost" className="text-slate-400" onClick={() => setJobId(null)}>
          ← {t.researchVideo.backToResearch}
        </Button>
        <motion.div variants={fadeUpVariants} transition={shellTransition}>
          <DubbingProgress jobId={jobId} />
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div initial="hidden" animate="show" variants={staggerVariants} className="space-y-6">
      <motion.div variants={fadeUpVariants} transition={shellTransition}>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold bg-gradient-to-br from-amber-400 to-orange-500 text-transparent bg-clip-text">
            {t.researchVideo.title}
          </h1>
          <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/40 uppercase text-[10px] tracking-wider">
            {t.researchVideo.hackathonBadge}
          </Badge>
        </div>
        <p className="text-slate-400 max-w-2xl flex items-center gap-2">
          {t.researchVideo.subtitle}
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-[10px] border border-blue-500/20 font-medium">
            <Sparkles className="w-2.5 h-2.5" /> {t.researchVideo.workflowBadge}
          </span>
        </p>
      </motion.div>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            key={error}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={shellTransition}
            className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-sm text-red-300"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div layout className="grid gap-3 md:grid-cols-4">
        {steps.map((step) => {
          const active = wizardStep === step.id;
          const complete = wizardStep > step.id;
          return (
            <motion.div
              layout
              key={step.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0, scale: active ? 1.01 : 1 }}
              transition={{ ...shellTransition, delay: step.id * 0.03 }}
              className={`rounded-xl border px-4 py-3 text-sm ${
                active
                  ? 'border-cyan-400/50 bg-cyan-500/10 text-cyan-100'
                  : complete
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100'
                    : 'border-white/10 bg-slate-900/70 text-slate-400'
              }`}
            >
              <p className="text-[11px] uppercase tracking-[0.22em]">{t.researchVideo.stepLabel} {step.id}</p>
              <div className="mt-1 flex items-center gap-2">
                {complete ? <CheckCircle2 className="h-4 w-4" /> : <Wand2 className="h-4 w-4" />}
                <span className="font-semibold">{step.label}</span>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <motion.div layout className="space-y-4">
          <motion.div layout variants={fadeUpVariants} transition={shellTransition} className="rounded-2xl border border-amber-500/20 bg-slate-900/80 p-5 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <Label className="text-sm font-semibold flex items-center gap-2">
                <Search className="w-4 h-4 text-amber-400" />
                {t.researchVideo.topicLabel}
              </Label>
              <Badge className="bg-white/5 text-slate-300 border-white/10">{t.researchVideo.stepTopic}</Badge>
            </div>
            <div className="flex gap-2 mb-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-[10px] border-amber-500/30 text-amber-300 hover:bg-amber-500/10"
                onClick={() => loadDemoScenario('marketing')}
                disabled={isResearching}
              >
                ⚡ {t.researchVideo.demoMarketing}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-[10px] border-amber-500/30 text-amber-300 hover:bg-amber-500/10"
                onClick={() => loadDemoScenario('gaming')}
                disabled={isResearching}
              >
                ⚡ {t.researchVideo.demoGaming}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-[10px] border-amber-500/30 text-amber-300 hover:bg-amber-500/10"
                onClick={() => loadDemoScenario('film')}
                disabled={isResearching}
              >
                ⚡ {t.researchVideo.demoFilm}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-[10px] border-white/10 text-slate-300 hover:bg-white/5"
                onClick={handleHackathonDemo}
                disabled={isResearching}
              >
                ✨ {t.researchVideo.tryDemo}
              </Button>
            </div>
            <Textarea
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
              }}
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
                <motion.span
                  initial={{ opacity: 0.7 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.8, repeat: Infinity, repeatType: 'reverse' }}
                  className="inline-flex items-center gap-2"
                >
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {phaseLabel(researchPhase)}
                </motion.span>
              ) : (
                t.researchVideo.researchBtn
              )}
            </Button>
            <AnimatePresence>
              {isResearching && researchStatus && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={shellTransition}
                  className="overflow-hidden rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100"
                >
                  <p className="font-semibold uppercase tracking-wide text-amber-300/90">{phaseLabel(researchPhase)}</p>
                  <p className="mt-1 text-slate-200">{researchStatus}</p>
                </motion.div>
              )}
            </AnimatePresence>
            <p className="text-[11px] text-slate-500">{t.researchVideo.researchHint}</p>
          </motion.div>

          <AnimatePresence>
            {summary && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={shellTransition}
              className="rounded-xl border border-white/10 bg-black/30 p-4 space-y-2"
            >
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
            </motion.div>
          )}
          </AnimatePresence>

          <AnimatePresence>
          {sources.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={shellTransition}
              className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-2 max-h-[220px] overflow-y-auto"
            >
              <p className="text-xs font-bold uppercase text-slate-500">{t.researchVideo.sourcesTitle}</p>
              {sources.map((s, i) => (
                <motion.div
                  key={`${s.title}-${i}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...shellTransition, delay: i * 0.03 }}
                  className="text-xs border-b border-white/5 pb-2 last:border-0"
                >
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
                </motion.div>
              ))}
            </motion.div>
          )}
          </AnimatePresence>

          <motion.div layout variants={fadeUpVariants} transition={shellTransition} className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 space-y-3">
            <Label className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              {t.researchVideo.scriptLabel}
            </Label>
            <Textarea
              value={script}
              onChange={(e) => {
                setScript(e.target.value);
                if (wizardStep > 2) {
                  setWizardStep(2);
                  setSceneReviewCards([]);
                }
              }}
              placeholder={t.researchVideo.scriptPlaceholder}
              className="min-h-[200px] bg-black/40 border-white/10 text-sm"
            />
            {wordCount > 0 && (
              <p className="text-[11px] text-slate-500">
                {wordCount} {t.common.words} · ~{estimatedDuration}
                {t.common.seconds} ({t.researchVideo.targetShort})
              </p>
            )}
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                className="bg-gradient-to-r from-purple-600 to-indigo-600"
                disabled={!script.trim() || isResearching}
                onClick={handleApproveScript}
              >
                {t.researchVideo.approveScript}
              </Button>
              {sceneReviewCards.length > 0 && (
                <Button type="button" variant="outline" onClick={handleApproveScript}>
                  {t.researchVideo.refreshSceneReview}
                </Button>
              )}
            </div>
            <p className="text-[11px] text-slate-500">{t.researchVideo.scriptApproveHint}</p>
          </motion.div>

          <AnimatePresence>
          {wizardStep >= 3 && sceneReviewCards.length > 0 && (
            <motion.div
              layout
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12 }}
              transition={shellTransition}
              className="rounded-2xl border border-cyan-500/20 bg-slate-900/80 p-5 space-y-3"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-cyan-100">{t.researchVideo.sceneReviewTitle}</p>
                  <p className="text-[11px] text-slate-400">{t.researchVideo.sceneReviewHint}</p>
                </div>
                <Badge className="bg-cyan-500/15 text-cyan-200 border-cyan-500/30">
                  {sceneReviewCards.length} {t.researchVideo.sceneCards}
                </Badge>
              </div>
              <motion.div layout className="grid grid-cols-2 gap-3 text-xs text-slate-400">
                <motion.div layout className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <p className="font-semibold text-slate-200">{t.researchVideo.sceneReviewReady}</p>
                  <p>{t.researchVideo.sceneReviewReadyHint}</p>
                </motion.div>
                <motion.div layout className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <p className="font-semibold text-slate-200">{t.researchVideo.sceneFallbackSafe}</p>
                  <p>{t.researchVideo.sceneFallbackSafeHint}</p>
                </motion.div>
              </motion.div>
              <Button type="button" className="w-full bg-cyan-600 hover:bg-cyan-500" onClick={handleContinueToRender}>
                {t.researchVideo.continueToRender}
              </Button>
            </motion.div>
          )}
          </AnimatePresence>
        </motion.div>

        <motion.div layout variants={fadeUpVariants} transition={{ ...shellTransition, delay: 0.08 }}>
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
          sceneReviewCards={sceneReviewCards}
          onScenePromptChange={handleScenePromptChange}
          onRegenerateScene={handleSceneRegenerate}
          onKeepScene={handleSceneKeep}
          onFallbackScene={handleSceneFallback}
          onSceneClipSelect={handleSceneClipSelect}
          disableSceneClipInputs={usePixverseClipFolder}
        />
        </motion.div>
      </div>

      <AnimatePresence>
      {wizardStep >= 4 && (
      <motion.div
        layout
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 12 }}
        transition={shellTransition}
        className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 space-y-4"
      >
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
        <div className="rounded-xl border border-white/10 bg-black/30 p-4 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-200">{t.researchVideo.pixverseFolderToggle}</p>
              <p className="text-[11px] text-slate-500">{t.researchVideo.pixverseFolderHint}</p>
            </div>
            <Switch
              checked={usePixverseClipFolder}
              onCheckedChange={(v) => {
                setUsePixverseClipFolder(v);
                if (v) setSceneClipFiles({});
              }}
            />
          </div>
          <p className="text-[11px] text-slate-500">
            {t.researchVideo.pixverseFolderPath}{' '}
            <span className="font-mono text-slate-300">storage/input/pixverse_smoke</span>
          </p>
          <p className="text-[11px] text-slate-500">{t.researchVideo.pixverseFolderRules}</p>
        </div>
        <p className="text-[11px] text-slate-500 leading-snug">{t.researchVideo.renderHint}</p>
        <Button
          className="w-full py-6 font-bold bg-gradient-to-r from-indigo-600 to-purple-600"
          disabled={isRendering || !script.trim() || !sceneReviewCards.length}
          onClick={() => void handleRender()}
        >
          {isRendering ? t.researchVideo.rendering : t.researchVideo.renderBtn}
        </Button>
      </motion.div>
      )}
      </AnimatePresence>
    </motion.div>
  );
}
