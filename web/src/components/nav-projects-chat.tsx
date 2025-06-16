"use client";

import { usePathname } from "next/navigation";
import { SidebarGroup } from "@/components/ui/sidebar";
import { ProjectsSidebar } from "@/components/navigation/project-sidebar";

export function NavProjectsChat() {
  const pathname = usePathname();

  // Only show on chat page
  if (pathname !== "/chat") {
    return null;
  }

  return (
    <SidebarGroup>
      <ProjectsSidebar />
    </SidebarGroup>
  );
}
