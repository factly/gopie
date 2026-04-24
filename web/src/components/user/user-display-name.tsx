"use client";

import { usePublicUser } from "@/lib/queries/user/get-public-user";
import { Skeleton } from "@/components/ui/skeleton";

const isAuthEnabled =
  String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";

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
  const { data, isLoading } = usePublicUser({
    variables: { userId },
    enabled: isAuthEnabled && !!userId,
  });

  if (!isAuthEnabled) {
    return <span className={className}>{fallback ?? "System"}</span>;
  }

  if (isLoading) {
    return <Skeleton className="h-4 w-24 inline-block" />;
  }

  const displayName = data?.data?.displayName || fallback || userId;

  return <span className={className}>{displayName}</span>;
}
