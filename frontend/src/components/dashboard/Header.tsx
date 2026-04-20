interface HeaderProps {
    currentView: string;
}

const VIEW_NAMES: Record<string, string> = {
    dashboard: "Create New Project",
    projects: "My Projects",
    history: "Activity History",
    settings: "Settings",
    help: "Help & Support"
};

export function DashboardHeader({ currentView }: HeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/5 px-6 sticky top-0 bg-[#070a14]/90 backdrop-blur-md z-12">
      <div className="flex items-center gap-2 text-sm font-medium">
         <span className="text-slate-400">Dubify App</span>
         <span className="text-slate-600">/</span>
         <span className="text-white">{VIEW_NAMES[currentView] || "New Project"}</span>
      </div>
    </header>
  );
}
