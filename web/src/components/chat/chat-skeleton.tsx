import { Skeleton } from "@/components/ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="flex-1 overflow-hidden flex flex-col p-4 space-y-4">
      {/* Simulate a user message skeleton */}
      <div className="flex justify-end">
        <div className="max-w-[70%] space-y-2">
          <Skeleton className="h-4 w-[200px] bg-primary/10" />
          <Skeleton className="h-4 w-[150px] bg-primary/10" />
        </div>
      </div>

      {/* Simulate an assistant message skeleton */}
      <div className="flex justify-start">
        <div className="max-w-[70%] space-y-2">
          <Skeleton className="h-4 w-[300px]" />
          <Skeleton className="h-4 w-[250px]" />
          <Skeleton className="h-4 w-[280px]" />
        </div>
      </div>

      {/* Another user message */}
      <div className="flex justify-end">
        <div className="max-w-[70%] space-y-2">
          <Skeleton className="h-4 w-[180px] bg-primary/10" />
        </div>
      </div>

      {/* Another assistant message with code block */}
      <div className="flex justify-start">
        <div className="max-w-[70%] space-y-3">
          <Skeleton className="h-4 w-[320px]" />
          <Skeleton className="h-4 w-[290px]" />
          {/* Simulate a code block */}
          <Skeleton className="h-24 w-full rounded-md" />
          <Skeleton className="h-4 w-[260px]" />
        </div>
      </div>
    </div>
  );
}