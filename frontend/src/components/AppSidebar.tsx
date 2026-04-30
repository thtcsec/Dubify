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
           <div className="mb-6 px-3 flex items-center gap-3">
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <span className="font-bold">D</span>
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <span className="font-bold text-lg">DUBIFY</span>
                <span className="text-xs text-muted-foreground">AI Translator</span>
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
                className={`h-10 w-full justify-start gap-3 rounded-lg border ${
                  currentView === item.id
                    ? 'border-white/20 bg-white/10 text-white'
                    : 'border-transparent text-white/70 hover:bg-white/10 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-3'}`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!isCollapsed && <span>{item.title}</span>}
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
                className={`h-10 w-full justify-start gap-3 rounded-lg border ${
                  currentView === item.id
                    ? 'border-white/20 bg-white/10 text-white'
                    : 'border-transparent text-white/70 hover:bg-white/10 hover:text-white'
                } ${isCollapsed ? 'px-2' : 'px-3'}`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!isCollapsed && <span>{item.title}</span>}
              </Button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
