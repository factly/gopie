"use client";

import * as React from "react";
import { type LucideIcon } from "lucide-react";
import Link from "next/link";
import * as Sentry from "@sentry/nextjs";

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

export function NavSecondary({
  items,
  ...props
}: {
  items: {
    title: string;
    url: string;
    icon: LucideIcon;
  }[];
} & React.ComponentPropsWithoutRef<typeof SidebarGroup>) {
  
  const handleReportIssueClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    
    // Check if Sentry is configured and enabled
    const sentryDSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
    const client = Sentry.getCurrentScope().getClient();
    const isSentryEnabled = sentryDSN && client && client.getOptions().enabled !== false;
    
    if (isSentryEnabled) {
      // Use Sentry feedback if available
      const feedback = Sentry.getFeedback();
      if (feedback) {
        try {
          // Create and open the form directly
          const form = await feedback.createForm();
          form.appendToDom();
          form.open();
        } catch (error) {
          console.error("Error opening feedback form:", error);
          // Fallback to GitHub if Sentry feedback fails
          window.open("https://github.com/factly/gopie/issues", "_blank");
        }
      } else {
        // Fallback to GitHub if feedback widget is not available
        window.open("https://github.com/factly/gopie/issues", "_blank");
      }
    } else {
      // Open GitHub issues in a new tab when Sentry is not enabled
      window.open("https://github.com/factly/gopie/issues", "_blank");
    }
  };

  return (
    <SidebarGroup {...props}>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              {item.title === "Report Issue" ? (
                <SidebarMenuButton 
                  asChild={false} 
                  size="sm"
                  onClick={handleReportIssueClick}
                >
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              ) : (
                <SidebarMenuButton 
                  asChild
                  size="sm"
                >
                  <Link href={item.url}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              )}
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
