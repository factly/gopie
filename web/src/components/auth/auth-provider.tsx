"use client";

import * as React from "react";
import { useAuthStore } from "@/lib/stores/auth-store";

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkSession } = useAuthStore();

  React.useEffect(() => {
    // Check session on mount
    checkSession();
  }, [checkSession]);

  return <>{children}</>;
}
