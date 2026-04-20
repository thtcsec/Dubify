import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { History as HistoryIcon, User, Shield, Bell, HardDrive, Globe } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';

export function HistoryView() {
  const events = [
    { id: 1, action: "Project Created", detail: "Dubbed 'Intro_to_AI.mp4' to Vietnamese", date: "2 mins ago", type: "create" },
    { id: 2, action: "Download", detail: "Downloaded 'Marketing_Ad_EN.mp4'", date: "1 hour ago", type: "download" },
    { id: 3, action: "Login", detail: "New login from Chrome on Windows", date: "2 hours ago", type: "system" },
    { id: 4, action: "Import Failed", detail: "YouTube URL private or inaccessible", date: "Yesterday", type: "error" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Activity History</h1>
        <p className="text-slate-400">Track all your dubbing actions and system events.</p>
      </div>

      <Card className="bg-white/5 border-white/10">
        <CardContent className="p-0">
          {events.map((event, i) => (
            <div key={event.id} className={`p-4 flex gap-4 items-start ${i !== events.length - 1 ? 'border-b border-white/5' : ''}`}>
               <div className={`p-2 rounded-full ${
                 event.type === 'create' ? 'bg-green-500/10 text-green-400' :
                 event.type === 'error' ? 'bg-red-500/10 text-red-400' :
                 'bg-slate-500/10 text-slate-400'
               }`}>
                 <HistoryIcon className="w-4 h-4" />
               </div>
               <div className="flex-1">
                 <div className="flex justify-between items-center mb-1">
                   <h4 className="font-semibold text-sm">{event.action}</h4>
                   <span className="text-[10px] text-slate-500">{event.date}</span>
                 </div>
                 <p className="text-xs text-slate-400">{event.detail}</p>
               </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export function SettingsView() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-slate-400">Configure your personal preferences and AI providers.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-white/5 border-white/10">
          <CardHeader>
             <CardTitle className="flex items-center gap-2 text-lg"><User className="w-5 h-5 text-primary" /> Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             <div className="flex items-center justify-between">
                <Label>Public Profile</Label>
                <Switch defaultChecked />
             </div>
             <div className="flex items-center justify-between">
                <Label>Email Notifications</Label>
                <Switch defaultChecked />
             </div>
          </CardContent>
        </Card>

        <Card className="bg-white/5 border-white/10">
          <CardHeader>
             <CardTitle className="flex items-center gap-2 text-lg"><Globe className="w-5 h-5 text-primary" /> Region & Language</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             <div className="text-sm text-slate-400 space-y-2">
                <p>Default Target: <span className="text-white">Vietnamese (vi)</span></p>
                <p>Timezone: <span className="text-white">Asia/Ho_Chi_Minh</span></p>
             </div>
             <Button variant="outline" size="sm" className="w-full">Edit Locale Settings</Button>
          </CardContent>
        </Card>

        <Card className="bg-white/5 border-white/10 lg:col-span-2">
          <CardHeader>
             <CardTitle className="flex items-center gap-2 text-lg"><Shield className="w-5 h-5 text-primary" /> AI Provider API Keys</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             <p className="text-xs text-slate-500 mb-4">Leave empty to use built-in local models (WhisperX / EdgeTTS).</p>
             <div className="flex flex-col gap-4">
                <div className="space-y-2">
                   <Label className="text-xs">OpenAI API Key (Optional)</Label>
                   <div className="text-xs bg-black/40 p-3 rounded font-mono text-slate-600">sk-••••••••••••••••••••••••••••••••</div>
                </div>
                <div className="space-y-2">
                   <Label className="text-xs">Anthropic API Key (Optional)</Label>
                   <div className="text-xs bg-black/40 p-3 rounded font-mono text-slate-600">sk-ant-••••••••••••••••••••••••</div>
                </div>
             </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
