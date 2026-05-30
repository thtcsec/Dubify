import {
  LayoutDashboard,
  Layers,
  Clock,
  Settings,
  HelpCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  FlaskConical,
  Clapperboard,
  Wand2,
  Languages,
  LayoutTemplate,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { useI18n } from '@/i18n/I18nProvider';

const NAV_MAIN = [
  { id: 'dashboard', icon: LayoutDashboard },
  { id: 'studio', icon: Sparkles },
  { id: 'researchVideo', icon: FlaskConical, beta: true },
  { id: 'shorts', icon: Wand2 },
  { id: 'editor', icon: Clapperboard },
  { id: 'projects', icon: Layers },
  { id: 'history', icon: Clock },
] as const;

const NAV_SECONDARY = [
  { id: 'settings', icon: Settings },
  { id: 'help', icon: HelpCircle },
] as const;

const NAV_BOTTOM = [{ id: 'brandLayout', icon: LayoutTemplate }] as const;

interface AppSidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function AppSidebar({ currentView, onViewChange, isCollapsed, onToggleCollapse }: AppSidebarProps) {
  const { t, locale, setLocale } = useI18n();

  const navTitle = (id: string) => {
    const key = id as keyof typeof t.nav;
    return t.nav[key] ?? id;
  };

  return (
    <aside
      className={`border-r border-white/10 bg-[#02030a] transition-[width] duration-300 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex h-full flex-col p-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="mb-6 h-9 w-9 self-end text-white/70 hover:bg-white/10 hover:text-white"
          title={isCollapsed ? t.nav.expandSidebar : t.nav.collapseSidebar}
        >
          {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>

        {!isCollapsed && (
          <div className="mb-8 px-4 flex items-center gap-4 group cursor-pointer">
            <div className="relative flex aspect-square size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] group-hover:shadow-[0_0_20px_rgba(59,130,246,0.8)] transition-all">
              <span className="font-bold text-xl">D</span>
              <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/20" />
            </div>
            <div className="flex flex-col gap-0.5 leading-none">
              <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70">
                {t.common.appName.toUpperCase()}
              </span>
              <span className="text-[10px] uppercase tracking-widest font-bold text-blue-400">{t.common.tagline}</span>
            </div>
          </div>
        )}

        <div className="flex-1 space-y-1">
          {NAV_MAIN.map((item) => {
            const Icon = item.icon;
            return (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onViewChange(item.id)}
                className={`group relative h-11 w-full justify-start gap-3 rounded-xl border-0 overflow-hidden transition-all duration-300 ${
                  currentView === item.id ? 'text-white' : 'text-slate-400 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-4'}`}
              >
                <div
                  className={`absolute inset-0 transition-opacity duration-300 ${
                    currentView === item.id
                      ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 opacity-100'
                      : 'bg-white/5 opacity-0 group-hover:opacity-100'
                  }`}
                />
                {currentView === item.id && (
                  <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-gradient-to-b from-blue-400 to-purple-400 rounded-r-full shadow-[0_0_10px_rgba(96,165,250,0.8)]" />
                )}
                <Icon
                  className={`relative z-10 h-5 w-5 shrink-0 transition-transform duration-300 group-hover:scale-110 ${
                    currentView === item.id ? 'text-blue-400' : ''
                  }`}
                />
                {!isCollapsed && (
                  <span className="relative z-10 font-medium flex items-center gap-2 min-w-0">
                    <span className="truncate">{navTitle(item.id)}</span>
                    {'beta' in item && (item as { beta?: boolean }).beta && (
                      <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide bg-amber-500/25 text-amber-300 border border-amber-500/30">
                        Beta
                      </span>
                    )}
                  </span>
                )}
              </Button>
            );
          })}
        </div>

        <div className="pt-4 border-t border-white/10 space-y-1">
          {NAV_SECONDARY.map((item) => {
            const Icon = item.icon;
            return (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onViewChange(item.id)}
                className={`group relative h-11 w-full justify-start gap-3 rounded-xl border-0 overflow-hidden transition-all duration-300 ${
                  currentView === item.id ? 'text-white' : 'text-slate-400 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-4'}`}
              >
                <div
                  className={`absolute inset-0 transition-opacity duration-300 ${
                    currentView === item.id
                      ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 opacity-100'
                      : 'bg-white/5 opacity-0 group-hover:opacity-100'
                  }`}
                />
                {currentView === item.id && (
                  <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-gradient-to-b from-blue-400 to-purple-400 rounded-r-full shadow-[0_0_10px_rgba(96,165,250,0.8)]" />
                )}
                <Icon
                  className={`relative z-10 h-5 w-5 shrink-0 transition-transform duration-300 group-hover:scale-110 ${
                    currentView === item.id ? 'text-blue-400' : ''
                  }`}
                />
                {!isCollapsed && <span className="relative z-10 font-medium">{navTitle(item.id)}</span>}
              </Button>
            );
          })}

          <Button
            variant="ghost"
            onClick={() => setLocale(locale === 'vi' ? 'en' : 'vi')}
            className={`h-11 w-full justify-start gap-3 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 ${
              isCollapsed ? 'px-2' : 'px-4'
            }`}
            title={t.common.language}
          >
            <Languages className="h-5 w-5 shrink-0" />
            {!isCollapsed && (
              <span className="text-sm">{locale === 'vi' ? t.common.vietnamese : t.common.english}</span>
            )}
          </Button>

          {NAV_BOTTOM.map((item) => {
            const Icon = item.icon;
            return (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onViewChange(item.id)}
                className={`group relative h-11 w-full justify-start gap-3 rounded-xl border-0 overflow-hidden transition-all duration-300 ${
                  currentView === item.id ? 'text-white' : 'text-slate-400 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-4'}`}
              >
                <div
                  className={`absolute inset-0 transition-opacity duration-300 ${
                    currentView === item.id
                      ? 'bg-gradient-to-r from-cyan-500/20 to-indigo-500/20 opacity-100'
                      : 'bg-white/5 opacity-0 group-hover:opacity-100'
                  }`}
                />
                {currentView === item.id && (
                  <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-gradient-to-b from-cyan-400 to-indigo-400 rounded-r-full shadow-[0_0_10px_rgba(34,211,238,0.6)]" />
                )}
                <Icon
                  className={`relative z-10 h-5 w-5 shrink-0 transition-transform duration-300 group-hover:scale-110 ${
                    currentView === item.id ? 'text-cyan-400' : ''
                  }`}
                />
                {!isCollapsed && <span className="relative z-10 font-medium">{navTitle(item.id)}</span>}
              </Button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
