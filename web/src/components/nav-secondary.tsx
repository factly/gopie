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
  
  const handleFeedbackClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    
    // Get the feedback integration
    const feedback = Sentry.getFeedback();
    if (feedback) {
      try {
        // Create and open the form directly
        const form = await feedback.createForm();
        form.appendToDom();
        form.open();
      } catch (error) {
        console.error("Error opening feedback form:", error);
      }
    } else {
      // Fallback: use captureFeedback API if the widget is not available
      console.warn("Sentry feedback widget not available, please check configuration");
    }
  };

  return (
    <SidebarGroup {...props}>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              {item.title === "Report Bug/Feedback" ? (
                <SidebarMenuButton 
                  asChild={false} 
                  size="sm"
                  onClick={handleFeedbackClick}
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
