import { Card, CardContent } from '@/components/ui/card';
import { ExternalLink, Mail, MessageSquare, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function HelpView() {
  const faqs = [
    { q: "What video formats are supported?", a: "Dubify supports MP4, MOV, and AVI up to 500MB." },
    { q: "Which platforms can I import from?", a: "YouTube, Bilibili, Twitter (X), Douyin, and Google Drive (public links)." },
    { q: "How long does dubbing take?", a: "Usually 3-5 minutes for a 5-minute video, depending on server load." },
    { q: "Can I use my own API keys?", a: "Yes, you can configure OpenAI or Anthropic keys in Settings." },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Help & Support</h1>
        <p className="text-slate-400">Find answers and get help with the Dubify AI Platform.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-white/5 border-white/10 flex flex-col items-center text-center p-6">
          <BookOpen className="w-10 h-10 text-primary mb-4" />
          <h3 className="font-bold mb-2">Documentation</h3>
          <p className="text-xs text-slate-500 mb-6">Read our detailed guides on dubbing and translation.</p>
          <Button variant="outline" size="sm" className="w-full">Open Docs <ExternalLink className="w-3 h-3 ml-2" /></Button>
        </Card>

        <Card className="bg-white/5 border-white/10 flex flex-col items-center text-center p-6">
          <MessageSquare className="w-10 h-10 text-blue-400 mb-4" />
          <h3 className="font-bold mb-2">Community Discord</h3>
          <p className="text-xs text-slate-500 mb-6">Join our developer community to share tips and get news.</p>
          <Button variant="outline" size="sm" className="w-full">Join Discord <ExternalLink className="w-3 h-3 ml-2" /></Button>
        </Card>

        <Card className="bg-white/5 border-white/10 flex flex-col items-center text-center p-6">
          <Mail className="w-10 h-10 text-green-400 mb-4" />
          <h3 className="font-bold mb-2">Contact Support</h3>
          <p className="text-xs text-slate-500 mb-6">Having issues? Send our team an email directly.</p>
          <Button variant="outline" size="sm" className="w-full">Send Email <Mail className="w-3 h-3 ml-2" /></Button>
        </Card>
      </div>

      <div className="space-y-4 pt-4">
        <h2 className="text-xl font-bold">Frequently Asked Questions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {faqs.map((faq, i) => (
            <Card key={i} className="bg-white/5 border-white/10">
              <CardContent className="p-4">
                <h4 className="font-semibold text-sm mb-2">{faq.q}</h4>
                <p className="text-xs text-slate-400">{faq.a}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
