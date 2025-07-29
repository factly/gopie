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
  
  const handleFeedbackClick = (e: React.MouseEvent) => {
    e.preventDefault();
    
    // Get the feedback integration and create/show the widget
    const feedback = Sentry.getFeedback();
    if (feedback) {
      // Create and show the feedback widget
      feedback.createWidget();
      // The widget will automatically show when created
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
              <SidebarMenuButton 
                asChild={item.title !== "Feedback"} 
                size="sm"
                onClick={item.title === "Feedback" ? handleFeedbackClick : undefined}
              >
                {item.title === "Feedback" ? (
                  <button className="flex items-center gap-2 w-full">
                    <item.icon />
                    <span>{item.title}</span>
                  </button>
                ) : (
                  <Link href={item.url}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
