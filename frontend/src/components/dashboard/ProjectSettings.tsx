import { useEffect, useMemo, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import api from '@/lib/api';
import { parseVoicesResponse, type Voice } from '@/lib/voices';

const LANGUAGES = [
  { code: 'vi', name: 'Vietnamese' },
  { code: 'en', name: 'English' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ko', name: 'Korean' },
  { code: 'zh', name: 'Chinese' },
  { code: 'fr', name: 'French' },
  { code: 'es', name: 'Spanish' },
  { code: 'de', name: 'German' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'it', name: 'Italian' },
  { code: 'ru', name: 'Russian' },
  { code: 'th', name: 'Thai' },
  { code: 'hi', name: 'Hindi' },
  { code: 'ar', name: 'Arabic' },
  { code: 'id', name: 'Indonesian' },
];

interface ProjectSettingsProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
  voiceId: string;
  setVoiceId: (id: string) => void;
  projectName: string;
  setProjectName: (name: string) => void;
  suggestedProjectName?: string;
  isLoading: boolean;
  canStart: boolean;
  onStart: () => void;
}

export function ProjectSettings({
  targetLang,
  setTargetLang,
  voiceId,
  setVoiceId,
  projectName,
  setProjectName,
  suggestedProjectName = '',
  isLoading,
  canStart,
  onStart,
}: ProjectSettingsProps) {
  const { t } = useI18n();
  const [voices, setVoices] = useState<Voice[]>([]);

  useEffect(() => {
    api.get('/voices').then((res) => setVoices(parseVoicesResponse(res.data))).catch(() => {});
  }, []);

  const { viVoices, enVoices, otherVoices } = useMemo(() => {
    const vi = voices.filter((v) => v.category === 'vi' || (!v.category && v.lang === 'vi'));
    const en = voices.filter((v) => v.category === 'en' || (!v.category && v.lang === 'en'));
    const other = voices.filter(
      (v) =>
        !(v.category === 'vi' || (!v.category && v.lang === 'vi')) &&
        !(v.category === 'en' || (!v.category && v.lang === 'en')),
    );
    return { viVoices: vi, enVoices: en, otherVoices: other };
  }, [voices]);

  useEffect(() => {
    if (!voiceId && voices.length > 0) {
      const code = targetLang.split('-')[0];
      const match = voices.find((v) => v.lang === code || v.category === code);
      if (match) setVoiceId(match.id);
    }
  }, [targetLang, voices, voiceId, setVoiceId]);

  return (
    <div className="relative group h-full">
      <div className="absolute -inset-0.5 bg-gradient-to-b from-indigo-500/20 to-purple-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500" />
      <Card className="relative bg-slate-900/80 backdrop-blur-xl border border-white/10 text-white shadow-2xl h-full rounded-2xl flex flex-col">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <span className="bg-indigo-500/20 text-indigo-400 p-1.5 rounded-lg">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </span>
            {t.projectSettings.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 flex-1 flex flex-col justify-between">
          <div className="space-y-5">
            <div className="space-y-2">
              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">
                {t.projectSettings.projectName}
              </Label>
              <Input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder={suggestedProjectName || t.projectSettings.projectNamePlaceholder}
                className="bg-black/40 border-white/10 h-11"
                maxLength={120}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">
                {t.projectSettings.targetLanguage}
              </Label>
              <Select value={targetLang} onValueChange={setTargetLang}>
                <SelectTrigger className="bg-black/40 border-white/10 hover:border-white/20 transition-colors h-12 rounded-xl text-base px-4">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-white/10 rounded-xl shadow-2xl">
                  {LANGUAGES.map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {lang.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-slate-400 text-xs font-bold uppercase tracking-widest">
                {t.projectSettings.voice}
              </Label>
              <Select value={voiceId} onValueChange={setVoiceId}>
                <SelectTrigger className="bg-black/40 border-white/10 h-12 rounded-xl">
                  <SelectValue placeholder={t.projectSettings.voice} />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-white/10 max-h-72">
                  {viVoices.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Tiếng Việt</SelectLabel>
                      {viVoices.map((v) => (
                        <SelectItem key={v.id} value={v.id}>
                          {v.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {enVoices.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>English</SelectLabel>
                      {enVoices.map((v) => (
                        <SelectItem key={v.id} value={v.id}>
                          {v.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {otherVoices.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="pt-6 border-t border-white/10 space-y-4">
            <Button
              className="w-full btn-glow bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-7 rounded-xl text-lg shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_25px_rgba(79,70,229,0.5)] transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
              disabled={isLoading || !canStart}
              onClick={onStart}
            >
              {isLoading ? (
                <div className="flex items-center justify-center gap-3">
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>{t.projectSettings.processing}</span>
                </div>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 mr-1" /> {t.projectSettings.startDubbing}
                </span>
              )}
            </Button>
            <p className="text-xs text-center text-slate-500 font-medium">
              Estimated time: 3-5 mins depending on hardware
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
