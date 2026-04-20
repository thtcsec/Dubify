import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const LANGUAGES = [
  { code: 'vi', name: 'Vietnamese' },
  { code: 'en', name: 'English' },
  { code: 'ru', name: 'Russian' },
  { code: 'de', name: 'German' },
  { code: 'fr', name: 'French' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ja', name: 'Japanese' },
];

interface ProjectSettingsProps {
  targetLang: string;
  setTargetLang: (lang: string) => void;
  isLoading: boolean;
  canStart: boolean;
  onStart: () => void;
}

export function ProjectSettings({
  targetLang,
  setTargetLang,
  isLoading,
  canStart,
  onStart
}: ProjectSettingsProps) {
  return (
    <Card className="bg-white/5 border-white/10 text-white shadow-xl h-fit">
      <CardHeader>
        <CardTitle className="text-lg">Project Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label className="text-slate-400">Target Language</Label>
          <Select value={targetLang} onValueChange={setTargetLang}>
            <SelectTrigger className="bg-white/10 border-white/10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGES.map(lang => (
                <SelectItem key={lang.code} value={lang.code}>{lang.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="pt-4 space-y-4">
          <Button 
            className="w-full h-14 text-lg font-bold shadow-lg shadow-primary/30" 
            disabled={isLoading || !canStart}
            onClick={onStart}
          >
            <Sparkles className="w-5 h-5 mr-2" /> Start Dubbing
          </Button>
          <p className="text-[10px] text-center text-slate-500">
            Estimated time: 3-5 mins depending on hardware
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
