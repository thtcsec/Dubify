import { Card, CardContent } from '@/components/ui/card';
import { ExternalLink, Mail, MessageSquare, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/i18n/I18nProvider';

export function HelpView() {
  const { t } = useI18n();
  const faqs = [
    { q: t.help.formatsQ, a: t.help.formatsA },
    { q: t.help.platformsQ, a: t.help.platformsA },
    { q: t.help.durationQ, a: t.help.durationA },
    { q: t.help.keysQ, a: t.help.keysA },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">{t.help.title}</h1>
        <p className="text-slate-400">{t.help.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-white/5 border-white/10 flex flex-col items-center text-center p-6">
          <BookOpen className="w-10 h-10 text-primary mb-4" />
          <h3 className="font-bold mb-2">{t.help.docs}</h3>
          <p className="text-xs text-slate-500 mb-6">{t.help.docsDesc}</p>
          <Button variant="outline" size="sm" className="w-full">
            {t.help.openDocs} <ExternalLink className="w-3 h-3 ml-2" />
          </Button>
        </Card>

        <Card className="bg-white/5 border-white/10 flex flex-col items-center text-center p-6">
          <MessageSquare className="w-10 h-10 text-blue-400 mb-4" />
          <h3 className="font-bold mb-2">{t.help.discord}</h3>
          <p className="text-xs text-slate-500 mb-6">{t.help.discordDesc}</p>
          <Button variant="outline" size="sm" className="w-full">
            {t.help.joinDiscord} <ExternalLink className="w-3 h-3 ml-2" />
          </Button>
        </Card>

        <Card className="bg-white/5 border-white/10 flex flex-col items-center text-center p-6">
          <Mail className="w-10 h-10 text-green-400 mb-4" />
          <h3 className="font-bold mb-2">{t.help.contact}</h3>
          <p className="text-xs text-slate-500 mb-6">{t.help.contactDesc}</p>
          <Button variant="outline" size="sm" className="w-full">
            {t.help.sendEmail} <Mail className="w-3 h-3 ml-2" />
          </Button>
        </Card>
      </div>

      <div className="space-y-4 pt-4">
        <h2 className="text-xl font-bold">{t.help.faqTitle}</h2>
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
