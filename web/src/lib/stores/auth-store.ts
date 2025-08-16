import { create } from "zustand";
import { persist } from "zustand/middleware";
import { ZitadelUser } from "@/lib/auth/zitadel-client";
import {
  setGlobalAccessToken,
  setGlobalOrganizationId,
} from "@/lib/api-client";

interface AuthState {
  user: ZitadelUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  accessToken: string | null;
  organizationId: string | null;

  // Actions
  login: (loginName: string, password: string) => Promise<{ success: boolean; userId: string; isMFAEnabled: boolean; error?: string; callbackUrl: string }>;
  loginWithOAuth: (returnUrl?: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (userData: {
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    password: string;
  }) => Promise<{ success: boolean; userId: string; error?: string }>;
  checkSession: () => Promise<void>;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      accessToken: null,
      organizationId: null,

      login: async (loginName, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ loginName, password }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error || "Login failed");
          }

          if (!data.isMFAEnabled && data.user) {
            set({ isAuthenticated: true, user: data.user, accessToken: data.accessToken });
            setGlobalAccessToken(data.accessToken);
          }

          return { success: true, userId: data.userId, isMFAEnabled: data.isMFAEnabled, callbackUrl: data.callbackUrl };
        } catch (error: any) {
          set({
            error: error.message,
            isLoading: false,
            isAuthenticated: false,
            user: null,
            accessToken: null,
          });
          setGlobalAccessToken(null);
          return { success: false, userId: '', isMFAEnabled: false, error: error.message, callbackUrl: '' };
        } finally {
          set({ isLoading: false });
        }
      },

      loginWithOAuth: async (returnUrl?: string): Promise<void> => {
        set({ isLoading: true, error: null });

        try {
          const baseUrl = window.location.origin;
          const successUrl = `${baseUrl}/api/oauth/callback${
            returnUrl ? `?returnUrl=${encodeURIComponent(returnUrl)}` : ""
          }`;
          const failureUrl = `${baseUrl}/auth/login?error=oauth_failed`;

          const response = await fetch("/api/oauth/initiate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ successUrl, failureUrl }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error || "Failed to initiate OAuth");
          }

          // Redirect to Google OAuth
          window.location.href = data.authUrl;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "OAuth login failed";
          set({
            error: errorMessage,
            isLoading: false,
          });
        }
      },

      register: async (userData: {
        firstName: string;
        lastName: string;
        email: string;
        password?: string;
      }): Promise<{ success: boolean; userId: string; error?: string }> => {
        set({ isLoading: true, error: null });

        try {
          const response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(userData),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error || "Registration failed");
          }

          set({ isLoading: false, error: null });
          return { success: true, userId: data.userId };
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Registration failed";
          set({
            error: errorMessage,
            isLoading: false,
          });
          return { success: false, error: errorMessage, userId: '' };
        }
      },

      logout: async (): Promise<void> => {
        set({ isLoading: true });

        try {
          await fetch("/api/auth/logout", {
            method: "POST",
          });
        } catch (error) {
          console.error("Logout error:", error);
        } finally {
          set({
            user: null,
            isAuthenticated: false,
            accessToken: null,
            organizationId: null,
            isLoading: false,
            error: null,
          });
          setGlobalAccessToken(null);
          setGlobalOrganizationId(null);
        }
      },

      checkSession: async (): Promise<void> => {
        try {
          const response = await fetch("/api/auth/session");

          if (response.ok) {
            const data = await response.json();
            set({
              user: data.user,
              isAuthenticated: true,
              accessToken: data.accessToken,
              organizationId: data.user.organizationId,
            });
            setGlobalAccessToken(data.accessToken);
            setGlobalOrganizationId(data.user.organisationId);
          } else {
            set({
              user: null,
              isAuthenticated: false,
              accessToken: null,
              organizationId: null,
            });
            setGlobalAccessToken(null);
            setGlobalOrganizationId(null);
          }
        } catch (error) {
          console.error("Session check error:", error);
          set({
            user: null,
            isAuthenticated: false,
            accessToken: null,
            organizationId: null,
          });
          setGlobalAccessToken(null);
          setGlobalOrganizationId(null);
        }
      },

      setError: (error: string | null) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
        organizationId: state.organizationId,
      }),
    }
  )
);
