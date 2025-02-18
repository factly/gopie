import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

interface VisuallyHiddenProps {
  asChild?: boolean;
  className?: string;
  children: React.ReactNode;
}

export function VisuallyHidden({
  asChild,
  className,
  children,
  ...props
}: VisuallyHiddenProps) {
  const Comp = asChild ? Slot : "span";

  return (
    <Comp
      className={cn(
        "absolute h-px w-px p-0 -m-px overflow-hidden whitespace-nowrap border-0",
        className
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}
