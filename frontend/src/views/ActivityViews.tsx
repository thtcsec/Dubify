import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { History as HistoryIcon, Shield, HardDrive, Globe, Eye, EyeOff, Loader2 } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

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
  const [config, setConfig] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showOpenAI, setShowOpenAI] = useState(false);
  const [showAnthropic, setShowAnthropic] = useState(false);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await api.get('/settings');
        setConfig(response.data);
      } catch (err) {
        console.error('Failed to fetch config');
      } finally {
        setIsLoading(false);
      }
    };
    fetchConfig();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin mb-4" />
        <p>Loading configuration...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">System Settings</h1>
        <p className="text-slate-400">Manage your local environment and AI provider keys.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Environment Paths */}
        <Card className="bg-white/5 border-white/10 lg:col-span-2">
          <CardHeader>
             <CardTitle className="flex items-center gap-2 text-lg"><HardDrive className="w-5 h-5 text-primary" /> Environment Paths</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                   <Label className="text-[10px] uppercase text-slate-500">Project Root</Label>
                   <p className="text-xs font-mono bg-black/20 p-2 rounded truncate">{config?.base_dir}</p>
                </div>
                <div className="space-y-1">
                   <Label className="text-[10px] uppercase text-slate-500">Storage Directory</Label>
                   <p className="text-xs font-mono bg-black/20 p-2 rounded truncate">{config?.storage_dir}</p>
                </div>
                <div className="space-y-1">
                   <Label className="text-[10px] uppercase text-slate-500">Models Directory</Label>
                   <p className="text-xs font-mono bg-black/20 p-2 rounded truncate">{config?.models_dir}</p>
                </div>
                <div className="space-y-1">
                   <Label className="text-[10px] uppercase text-slate-500">Project Name</Label>
                   <p className="text-xs font-mono bg-black/20 p-2 rounded">{config?.project_name}</p>
                </div>
             </div>
          </CardContent>
        </Card>

        {/* AI Models */}
        <Card className="bg-white/5 border-white/10">
          <CardHeader>
             <CardTitle className="flex items-center gap-2 text-lg"><Globe className="w-5 h-5 text-primary" /> Default Models</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             <div className="space-y-1">
                <Label className="text-[10px] uppercase text-slate-500">Whisper ASR</Label>
                <p className="text-sm font-semibold">{config?.whisper_model}</p>
             </div>
             <div className="space-y-1">
                <Label className="text-[10px] uppercase text-slate-500">NLLB Translation</Label>
                <p className="text-sm font-semibold truncate">{config?.nllb_model}</p>
             </div>
          </CardContent>
        </Card>

        {/* API Keys */}
        <Card className="bg-white/5 border-white/10 lg:col-span-3">
          <CardHeader>
             <CardTitle className="flex items-center gap-2 text-lg"><Shield className="w-5 h-5 text-primary" /> AI Provider API Keys</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
             <p className="text-xs text-slate-500">These keys are loaded from your root <code className="text-primary">.env</code> file. Environment variables are read-only here.</p>
             
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                   <Label className="text-xs text-slate-400">OpenAI API Key</Label>
                   <div className="relative group">
                      <input 
                        type={showOpenAI ? "text" : "password"} 
                        readOnly 
                        value={config?.openai_api_key || ""}
                        className="w-full bg-black/40 border border-white/5 rounded-lg px-4 py-3 pr-12 text-xs font-mono text-slate-300 outline-none"
                        placeholder="Not set in .env"
                      />
                      <button 
                        onClick={() => setShowOpenAI(!showOpenAI)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-2 hover:bg-white/5 rounded-md transition-colors"
                      >
                        {showOpenAI ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                   </div>
                </div>

                <div className="space-y-2">
                   <Label className="text-xs text-slate-400">Anthropic API Key</Label>
                   <div className="relative group">
                      <input 
                        type={showAnthropic ? "text" : "password"} 
                        readOnly 
                        value={config?.anthropic_api_key || ""}
                        className="w-full bg-black/40 border border-white/5 rounded-lg px-4 py-3 pr-12 text-xs font-mono text-slate-300 outline-none"
                        placeholder="Not set in .env"
                      />
                      <button 
                        onClick={() => setShowAnthropic(!showAnthropic)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-2 hover:bg-white/5 rounded-md transition-colors"
                      >
                        {showAnthropic ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                   </div>
                </div>
             </div>
             
             <div className="pt-4 border-t border-white/5">
                <p className="text-[10px] text-slate-600">To change these values, please edit the <code className="bg-white/5 px-1 rounded">.env</code> file in your project root and restart the server.</p>
             </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
