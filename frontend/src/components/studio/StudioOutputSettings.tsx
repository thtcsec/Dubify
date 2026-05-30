import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useI18n } from '@/i18n/I18nProvider';
import { ASPECT_RATIO_OPTIONS, type AspectRatioValue } from '@/lib/aspectRatios';
import type { Voice } from '@/lib/voices';

export interface StudioOutputSettingsProps {
  targetLang: string;
  setTargetLang: (v: string) => void;
  selectedVoice: string;
  setSelectedVoice: (v: string) => void;
  viVoices: Voice[];
  enVoices: Voice[];
  otherVoices: Voice[];
  voiceList: Voice[];
  studioVisualMode: 'html_scenes' | 'classic';
  setStudioVisualMode: (v: 'html_scenes' | 'classic') => void;
  studioRenderEngine: 'auto' | 'playwright' | 'hyperframes';
  setStudioRenderEngine: (v: 'auto' | 'playwright' | 'hyperframes') => void;
  aspectRatio: AspectRatioValue;
  setAspectRatio: (v: AspectRatioValue) => void;
  wordCount: number;
  estimatedDuration: number;
  autoEstimatedDuration: number;
  manualDuration: number | null;
  setManualDuration: (v: number | null) => void;
  isPreviewPlaying: boolean;
  onPreviewVoice: () => void;
}

export function StudioOutputSettings(props: StudioOutputSettingsProps) {
  const {
    targetLang,
    setTargetLang,
    selectedVoice,
    setSelectedVoice,
    viVoices,
    enVoices,
    otherVoices,
    voiceList,
    studioVisualMode,
    setStudioVisualMode,
    studioRenderEngine,
    setStudioRenderEngine,
    aspectRatio,
    setAspectRatio,
    wordCount,
    estimatedDuration,
    autoEstimatedDuration,
    manualDuration,
    setManualDuration,
    isPreviewPlaying,
    onPreviewVoice,
  } = props;

  const { t } = useI18n();
  const aspectLabel = (value: string) => {
    const key = value.replace(':', '_') as '16_9' | '9_16' | '4_3' | '3_4' | '1_1';
    return t.brandLayout.ratios[key] ?? value;
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div className="space-y-1.5">
        <Label className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
          {t.studio.configLanguage}
        </Label>
        <Select
          value={targetLang}
          onValueChange={(v) => {
            setTargetLang(v);
            const pool = v === 'en' ? enVoices : v === 'vi' ? viVoices : voiceList;
            const firstMatch = pool[0] ?? voiceList.find((voice) => voice.lang === v);
            if (firstMatch) setSelectedVoice(firstMatch.id);
          }}
        >
          <SelectTrigger className="w-full bg-black/40 border-white/10 h-10 rounded-lg text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-white/10">
            <SelectItem value="vi">🇻🇳 Vietnamese</SelectItem>
            <SelectItem value="en">🇺🇸 English</SelectItem>
            <SelectItem value="ja">🇯🇵 Japanese</SelectItem>
            <SelectItem value="ko">🇰🇷 Korean</SelectItem>
            <SelectItem value="zh">🇨🇳 Chinese</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
          {t.studio.configVoice}
        </Label>
        <div className="flex gap-2">
          <Select value={selectedVoice} onValueChange={setSelectedVoice}>
            <SelectTrigger className="flex-1 bg-black/40 border-white/10 h-10 rounded-lg text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-white/10 max-h-72">
              {viVoices.length > 0 && (
                <SelectGroup>
                  <SelectLabel className="text-cyan-400/90">{t.studio.voiceGroupVi}</SelectLabel>
                  {viVoices.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.name}
                      {v.style ? ` · ${v.style}` : v.accent ? ` · ${v.accent}` : ''}
                    </SelectItem>
                  ))}
                </SelectGroup>
              )}
              {enVoices.length > 0 && (
                <SelectGroup>
                  <SelectLabel className="text-indigo-400/90">{t.studio.voiceGroupEn}</SelectLabel>
                  {enVoices.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.name}
                      {v.accent ? ` · ${v.accent}` : ''}
                      {v.style ? ` — ${v.style}` : ''}
                    </SelectItem>
                  ))}
                </SelectGroup>
              )}
              {otherVoices.length > 0 && (
                <SelectGroup>
                  <SelectLabel className="text-slate-400">{t.studio.voiceGroupOther}</SelectLabel>
                  {otherVoices.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.name} · {v.accent || v.lang}
                    </SelectItem>
                  ))}
                </SelectGroup>
              )}
            </SelectContent>
          </Select>
          <Button type="button" variant="outline" className="h-10 w-10 shrink-0" onClick={onPreviewVoice}>
            {isPreviewPlaying ? '❚❚' : '▶'}
          </Button>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
          {t.studio.configAspect}
        </Label>
        <Select value={aspectRatio} onValueChange={(v) => setAspectRatio(v as AspectRatioValue)}>
          <SelectTrigger className="bg-black/40 border-white/10 h-10 rounded-lg text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-white/10">
            {ASPECT_RATIO_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {aspectLabel(opt.value)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
          {t.studio.visualMode}
        </Label>
        <Select value={studioVisualMode} onValueChange={(v) => setStudioVisualMode(v as 'html_scenes' | 'classic')}>
          <SelectTrigger className="bg-black/40 border-white/10 h-10 rounded-lg text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-white/10">
            <SelectItem value="html_scenes">{t.studio.modeHtmlScenes}</SelectItem>
            <SelectItem value="classic">{t.studio.modeClassic}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {studioVisualMode === 'html_scenes' && (
        <div className="space-y-1.5">
          <Label className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
            {t.studio.renderEngine}
          </Label>
          <Select
            value={studioRenderEngine}
            onValueChange={(v) => setStudioRenderEngine(v as 'auto' | 'playwright' | 'hyperframes')}
          >
            <SelectTrigger className="bg-black/40 border-white/10 h-10 rounded-lg text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-white/10">
              <SelectItem value="auto">{t.studio.renderAuto}</SelectItem>
              <SelectItem value="hyperframes">{t.studio.renderHyperframes}</SelectItem>
              <SelectItem value="playwright">{t.studio.renderPlaywright}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {wordCount > 0 && (
        <div className="space-y-1.5 sm:col-span-2 lg:col-span-3">
          <div className="flex items-center justify-between">
            <Label className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
              {t.studio.configTiming}
            </Label>
            <span className="text-xs font-mono text-purple-400">
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
              className="flex-1 h-1.5 accent-purple-500"
            />
            {manualDuration !== null && (
              <button
                type="button"
                className="text-[10px] text-slate-500 hover:text-purple-400 whitespace-nowrap"
                onClick={() => setManualDuration(null)}
              >
                {t.studio.resetTiming}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
