import { useI18n } from '@/i18n/I18nProvider';
import { AnimatePresence, motion } from 'framer-motion';

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
        <AnimatePresence mode="wait">
          <motion.span
            key={currentView}
            initial={{ opacity: 0, y: 6, filter: 'blur(4px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -6, filter: 'blur(4px)' }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="text-white"
          >
            {title}
          </motion.span>
        </AnimatePresence>
      </div>
    </header>
  );
}
