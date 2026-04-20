import { SidebarTrigger } from "@/components/ui/sidebar";

export function DashboardHeader() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b border-white/5 px-4 sticky top-0 bg-slate-950/80 backdrop-blur-md z-12">
      <SidebarTrigger className="-ml-1 text-slate-400" />
      <div className="h-4 w-px bg-white/10 mx-2" />
      <div className="flex items-center gap-2 text-sm font-medium">
         <span className="text-slate-400">Dashboard</span>
         <span className="text-slate-600">/</span>
         <span className="text-white">Create New Project</span>
      </div>
    </header>
  );
}
