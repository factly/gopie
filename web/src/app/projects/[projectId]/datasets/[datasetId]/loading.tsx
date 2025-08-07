import { Skeleton } from "@/components/ui/skeleton";

export default function DatasetLoading() {
  return (
    <div className="py-10">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Loading Header */}
        <div className="bg-background p-8 shadow-sm border">
          <div className="space-y-6">
            {/* Breadcrumb Skeleton */}
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4 w-32" />
            </div>

            {/* Main Header Skeleton */}
            <div className="flex items-start gap-6">
              {/* Left Section */}
              <div className="flex items-start gap-4 flex-1">
                <Skeleton className="h-12 w-12" />
                <div className="space-y-3 flex-1">
                  {/* Title */}
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-7 w-7" />
                    <Skeleton className="h-6 w-12 rounded" />
                  </div>
                  {/* Description */}
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </div>
                  {/* Quick Stats */}
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-5 w-16" />
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-7 w-24" />
                  </div>
                </div>
              </div>
              {/* Right Section - Action Buttons */}
              <div className="flex items-center gap-2">
                <Skeleton className="h-9 w-9" />
                <Skeleton className="h-9 w-9" />
                <Skeleton className="h-9 w-9" />
              </div>
            </div>
          </div>
        </div>

        {/* Loading Content */}
        <div className="bg-background shadow-sm border overflow-hidden">
          <div className="px-6 pt-6">
            <Skeleton className="h-9 w-[400px]" />
          </div>
          <div className="p-6 pt-4">
            <Skeleton className="h-[400px] w-full" />
          </div>
        </div>
      </div>
    </div>
  );
}