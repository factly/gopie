import { useAuthStore } from "@/lib/stores/auth-store";

export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const organizationId = useAuthStore((state) => state.organizationId);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const checkSession = useAuthStore((state) => state.checkSession);

  return {
    user,
    organizationId,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    checkSession,
  };
}
