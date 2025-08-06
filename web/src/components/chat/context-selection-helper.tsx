"use client";

import React from "react";
import { motion } from "framer-motion";

interface ContextSelectionHelperProps {
  isVisible: boolean;
}

export function ContextSelectionHelper({ isVisible }: ContextSelectionHelperProps) {
  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mt-3 flex items-center gap-2 text-sm text-muted-foreground"
    >
      <div className="flex items-center gap-1">
        <svg 
          className="w-4 h-4 text-primary animate-bounce" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M7 11l5-5m0 0l5 5m-5-5v12" 
          />
        </svg>
        <span className="text-primary font-medium">Click here</span>
      </div>
      <span>to select at least one project or dataset to continue</span>
    </motion.div>
  );
}