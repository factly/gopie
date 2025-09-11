"use client";

import { usePathname } from "next/navigation";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { AppHeader } from "@/components/app-header";

export function ConditionalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname?.startsWith("/auth");
  const isLandingPage = pathname === "/";
  const isChatPage = pathname.startsWith("/chat");
  const chatStyles = isChatPage ? "overflow-hidden" : "";

  // Don't show sidebar on auth pages or landing page
  if (isAuthPage || isLandingPage) {
    return <div className="min-h-screen bg-background">{children}</div>;
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className={chatStyles}>
        <AppHeader/>
        {children}
      </SidebarInset>
    </SidebarProvider>
  );
}