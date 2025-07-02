"use client";

import React from "react";
import { Globe, Lock, Building2 } from "lucide-react";
import { ChatVisibility } from "@/lib/mutations/chat";
import { cn } from "@/lib/utils";

interface ChatVisibilityIndicatorProps {
  visibility?: ChatVisibility;
  className?: string;
}

const visibilityConfig = {
  private: {
    icon: Lock,
    label: "Private",
    className: "text-muted-foreground",
  },
  organization: {
    icon: Building2,
    label: "Organization",
    className: "text-blue-500",
  },
  public: {
    icon: Globe,
    label: "Public",
    className: "text-green-500",
  },
};

export function ChatVisibilityIndicator({
  visibility = "private",
  className,
}: ChatVisibilityIndicatorProps) {
  const config = visibilityConfig[visibility];
  const Icon = config.icon;

  return (
    <div title={config.label} className="inline-flex">
      <Icon className={cn("h-3 w-3", config.className, className)} />
    </div>
  );
}
