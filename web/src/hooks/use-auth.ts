import { useAuthStore } from "@/lib/stores/auth-store";
import { setGlobalAccessToken } from "@/lib/api-client";
import { useEffect } from "react";

export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const accessToken = useAuthStore((state) => state.accessToken);
  const organizationId = useAuthStore((state) => state.organizationId);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const checkSession = useAuthStore((state) => state.checkSession);

  // Set global access token whenever it changes
  useEffect(() => {
    setGlobalAccessToken(accessToken);
  }, [accessToken]);

  return {
    user,
    accessToken,
    organizationId,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    checkSession,
  };
}
