"use client";

import { useUserDetail } from "@/lib/queries/user/get-user-detail";
import { Skeleton } from "@/components/ui/skeleton";

interface UserDisplayNameProps {
  userId: string;
  fallback?: string;
  className?: string;
}

export function UserDisplayName({
  userId,
  fallback,
  className,
}: UserDisplayNameProps) {
  const { data, isLoading } = useUserDetail({
    variables: { userId },
    enabled: !!userId,
  });

  if (isLoading) {
    return <Skeleton className="h-4 w-24 inline-block" />;
  }

  const displayName = data?.user?.human?.profile?.displayName || fallback || userId;

  return <span className={className}>{displayName}</span>;
}
