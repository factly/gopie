import { cn } from "@/lib/utils";

interface LoadingProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  text?: string;
  showText?: boolean;
}

export function Loading({
  className,
  size = "md",
  text = "Loading...",
  showText = true,
}: LoadingProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3",
        className
      )}
    >
      {/* Animated spinner */}
      <div className="relative">
        <div
          className={cn(
            "animate-spin rounded-full border-2 border-primary/20 border-t-primary",
            sizeClasses[size]
          )}
        />
        <div
          className={cn(
            "absolute inset-0 animate-ping rounded-full bg-primary/10",
            sizeClasses[size]
          )}
        />
      </div>

      {/* Animated text */}
      {showText && (
        <div className="flex items-center gap-1">
          <span className="animate-pulse text-sm font-medium text-muted-foreground">
            {text}
          </span>
          <div className="flex gap-0.5">
            <div className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]" />
            <div className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]" />
            <div className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" />
          </div>
        </div>
      )}
    </div>
  );
}

// Page-level loading component with skeleton layout
export function PageLoading() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Header skeleton */}
      <div className="border-b bg-background/50 backdrop-blur-sm w-[80%] mx-auto">
        <div className="container flex h-14 items-center">
          <div className="w-8 h-8 bg-muted animate-pulse rounded" />
          <div className="ml-4 w-24 h-4 bg-muted animate-pulse rounded" />
          <div className="ml-auto w-32 h-8 bg-muted animate-pulse rounded" />
        </div>
      </div>

      {/* Main content area with loading */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <Loading size="lg" text="Authenticating" />
          <p className="mt-4 text-sm text-muted-foreground animate-pulse">
            Please wait while we verify your credentials...
          </p>
        </div>
      </div>
    </div>
  );
}

// Simple centered loading
export function CenteredLoading({ text }: { text?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <Loading text={text} />
    </div>
  );
}
