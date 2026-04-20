import * as React from "react"
import {
  LayoutDashboard,
  Layers,
  Clock,
  Settings,
  HelpCircle,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

const data = {
  navMain: [
    {
      id: "dashboard",
      title: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      id: "projects",
      title: "Projects",
      icon: Layers,
    },
    {
      id: "history",
      title: "History",
      icon: Clock,
    },
  ],
  navSecondary: [
    {
      id: "settings",
      title: "Settings",
      icon: Settings,
    },
    {
      id: "help",
      title: "Help",
      icon: HelpCircle,
    },
  ],
}

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  currentView: string;
  onViewChange: (view: string) => void;
}

export function AppSidebar({ currentView, onViewChange, ...props }: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader className="h-16 border-b border-sidebar-border/50">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="hover:bg-transparent" onClick={() => onViewChange("dashboard")}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <span className="font-bold">D</span>
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <span className="font-bold text-lg">DUBIFY</span>
                <span className="text-xs text-muted-foreground">AI Translator</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Application</SidebarGroupLabel>
          <SidebarMenu>
            {data.navMain.map((item) => (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton 
                  tooltip={item.title} 
                  isActive={currentView === item.id}
                  onClick={() => onViewChange(item.id)}
                >
                  {item.icon && <item.icon />}
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border/50 p-4">
        <SidebarMenu>
            {data.navSecondary.map((item) => (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton 
                  size="sm" 
                  isActive={currentView === item.id}
                  onClick={() => onViewChange(item.id)}
                >
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
