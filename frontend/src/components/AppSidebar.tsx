import {
  LayoutDashboard,
  Layers,
  Clock,
  Settings,
  HelpCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  Clapperboard,
  Wand2
} from "lucide-react";
import { Button } from "../components/ui/button";

const NAV_MAIN = [
  { id: "dashboard", title: "Dub Video", icon: LayoutDashboard },
  { id: "studio", title: "Script Video", icon: Sparkles },
  { id: "shorts", title: "Auto Shorts", icon: Wand2 },
  { id: "editor", title: "Studio", icon: Clapperboard },
  { id: "projects", title: "Projects", icon: Layers },
  { id: "history", title: "History", icon: Clock },
];

const NAV_SECONDARY = [
  { id: "settings", title: "Settings", icon: Settings },
  { id: "help", title: "Help", icon: HelpCircle },
];

interface AppSidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function AppSidebar({ currentView, onViewChange, isCollapsed, onToggleCollapse }: AppSidebarProps) {
  return (
    <aside
      className={`border-r border-white/10 bg-[#02030a] transition-[width] duration-300 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex h-full flex-col p-2">
        {/* Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="mb-6 h-9 w-9 self-end text-white/70 hover:bg-white/10 hover:text-white"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>

        {/* Brand */}
        {!isCollapsed && (
           <div className="mb-8 px-4 flex items-center gap-4 group cursor-pointer">
              <div className="relative flex aspect-square size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] group-hover:shadow-[0_0_20px_rgba(59,130,246,0.8)] transition-all">
                <span className="font-bold text-xl">D</span>
                <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/20"></div>
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70">DUBIFY</span>
                <span className="text-[10px] uppercase tracking-widest font-bold text-blue-400">AI Creator Studio</span>
              </div>
           </div>
        )}

        {/* Main Navigation */}
        <div className="flex-1 space-y-1">
          {NAV_MAIN.map((item) => {
            const Icon = item.icon;
            return (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onViewChange(item.id)}
                className={`group relative h-11 w-full justify-start gap-3 rounded-xl border-0 overflow-hidden transition-all duration-300 ${
                  currentView === item.id
                    ? 'text-white'
                    : 'text-slate-400 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-4'}`}
              >
                {/* Active/Hover Background */}
                <div className={`absolute inset-0 transition-opacity duration-300 ${
                  currentView === item.id
                    ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 opacity-100'
                    : 'bg-white/5 opacity-0 group-hover:opacity-100'
                }`}></div>
                
                {/* Active Indicator Line */}
                {currentView === item.id && (
                  <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-gradient-to-b from-blue-400 to-purple-400 rounded-r-full shadow-[0_0_10px_rgba(96,165,250,0.8)]"></div>
                )}

                <Icon className={`relative z-10 h-5 w-5 shrink-0 transition-transform duration-300 group-hover:scale-110 ${currentView === item.id ? 'text-blue-400' : ''}`} />
                {!isCollapsed && <span className="relative z-10 font-medium">{item.title}</span>}
              </Button>
            );
          })}
        </div>

        {/* Secondary Navigation */}
        <div className="pt-4 border-t border-white/10 space-y-1">
          {NAV_SECONDARY.map((item) => {
            const Icon = item.icon;
            return (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onViewChange(item.id)}
                className={`group relative h-11 w-full justify-start gap-3 rounded-xl border-0 overflow-hidden transition-all duration-300 ${
                  currentView === item.id
                    ? 'text-white'
                    : 'text-slate-400 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-4'}`}
              >
                {/* Active/Hover Background */}
                <div className={`absolute inset-0 transition-opacity duration-300 ${
                  currentView === item.id
                    ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 opacity-100'
                    : 'bg-white/5 opacity-0 group-hover:opacity-100'
                }`}></div>
                
                {/* Active Indicator Line */}
                {currentView === item.id && (
                  <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-gradient-to-b from-blue-400 to-purple-400 rounded-r-full shadow-[0_0_10px_rgba(96,165,250,0.8)]"></div>
                )}

                <Icon className={`relative z-10 h-5 w-5 shrink-0 transition-transform duration-300 group-hover:scale-110 ${currentView === item.id ? 'text-blue-400' : ''}`} />
                {!isCollapsed && <span className="relative z-10 font-medium">{item.title}</span>}
              </Button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
