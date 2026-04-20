import { useState } from 'react';
import { DubbingProgress } from './components/DubbingProgress';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Upload, Languages, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from './lib/api';

const LANGUAGES = [
  { code: 'vi', name: 'Vietnamese' },
  { code: 'en', name: 'English' },
  { code: 'ru', name: 'Russian' },
  { code: 'de', name: 'German' },
  { code: 'fr', name: 'French' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ja', name: 'Japanese' },
];

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [targetLang, setTargetLang] = useState('vi');
  const [jobId, setJobId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_lang', targetLang);

    try {
      const response = await api.post('/dub', formData);
      setJobId(response.data.job_id);
    } catch (err) {
      console.error('Upload failed', err);
      alert('Upload failed. Please check if backend is running.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-slate-900 to-black text-white p-8 font-sans">
      <header className="max-w-4xl mx-auto mb-16 text-center">
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-center gap-3 mb-4"
        >
          <div className="bg-primary p-3 rounded-2xl shadow-lg shadow-primary/40">
            <Languages className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-5xl font-black tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-400">
            DUBIFY
          </h1>
        </motion.div>
        <p className="text-slate-400 text-lg">AI-Powered Video Localization with Professional Precision</p>
      </header>

      <main className="max-w-2xl mx-auto">
        <AnimatePresence mode="wait">
          {!jobId ? (
            <motion.div
              key="upload"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
            >
              <Card className="border-2 border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl overflow-hidden">
                <CardHeader className="pb-8">
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-yellow-400" />
                    New Dubbing Task
                  </CardTitle>
                  <CardDescription>Upload your video and select the target language.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label className="text-slate-300">Target Language</Label>
                    <Select value={targetLang} onValueChange={setTargetLang}>
                      <SelectTrigger className="bg-white/10 border-white/10 h-12">
                        <SelectValue placeholder="Select language" />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGES.map(lang => (
                          <SelectItem key={lang.code} value={lang.code}>{lang.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-4">
                     <Label className="text-slate-300">Video File</Label>
                    <div 
                      className={`border-2 border-dashed rounded-xl p-12 transition-all cursor-pointer flex flex-col items-center justify-center gap-4 ${
                        file ? 'border-primary bg-primary/10' : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                      }`}
                      onClick={() => document.getElementById('video-upload')?.click()}
                    >
                      <Upload className={`w-10 h-10 ${file ? 'text-primary' : 'text-slate-500'}`} />
                      <div className="text-center">
                        <p className="font-medium">{file ? file.name : "Click to select video"}</p>
                        <p className="text-sm text-slate-500">MP4, MOV, or AVI (Max 500MB)</p>
                      </div>
                      <input 
                        id="video-upload" 
                        type="file" 
                        accept="video/*" 
                        className="hidden" 
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                      />
                    </div>
                  </div>

                  <Button 
                    className="w-full h-14 text-lg font-bold shadow-lg shadow-primary/30" 
                    disabled={!file || isUploading}
                    onClick={handleUpload}
                  >
                    {isUploading ? "Uploading..." : "Start Dubbing Project"}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ) : (
            <motion.div
              key="progress"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
            >
               <div className="text-center mb-8">
                  <Button variant="link" className="text-slate-400" onClick={() => setJobId(null)}>
                    ← Back to Upload
                  </Button>
               </div>
               <DubbingProgress 
                jobId={jobId} 
                onComplete={() => console.log('Done!')}
                onError={(err) => alert(err)}
               />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="mt-20 text-center text-slate-600 text-sm">
        &copy; 2026 Dubify AI &bull; Created by thtcsec &bull; Optimized for RTX GPUs
      </footer>
    </div>
  );
}
