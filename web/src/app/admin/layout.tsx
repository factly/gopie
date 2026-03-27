"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, isLoading, role } = useAuthStore();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.push("/auth/login");
      return;
    }
    if (role !== "admin") {
      router.push("/");
    }
  }, [isAuthenticated, isLoading, role, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
