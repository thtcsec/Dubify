import { useI18n } from '@/i18n/I18nProvider';

interface HeaderProps {
  currentView: string;
}

export function DashboardHeader({ currentView }: HeaderProps) {
  const { t } = useI18n();
  const viewKey = currentView as keyof typeof t.viewTitles;
  const title = t.viewTitles[viewKey] ?? t.viewTitles.default;

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/5 px-6 sticky top-0 bg-[#070a14]/90 backdrop-blur-md z-12">
      <div className="flex items-center gap-2 text-sm font-medium">
        <span className="text-slate-400">{t.header.breadcrumb}</span>
        <span className="text-slate-600">/</span>
        <span className="text-white">{title}</span>
      </div>
    </header>
  );
}
