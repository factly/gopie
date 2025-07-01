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
  sessionToken: string | null;
  accessToken: string | null;
  organizationId: string | null;

  // Actions
  login: (loginName: string, password: string) => Promise<boolean>;
  loginWithOAuth: (returnUrl?: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (userData: {
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    password: string;
  }) => Promise<boolean>;
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
      sessionToken: null,
      accessToken: null,
      organizationId: null,

      login: async (loginName: string, password: string): Promise<boolean> => {
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

          set({
            user: data.user,
            isAuthenticated: true,
            sessionToken: null, // sessionToken is managed via cookies
            accessToken: data.accessToken,
            organizationId: data.user.organizationId ?? null,
            isLoading: false,
            error: null,
          });

          setGlobalAccessToken(data.accessToken);
          setGlobalOrganizationId(data.user.organizationId ?? null);

          return true;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Login failed";
          set({
            error: errorMessage,
            isLoading: false,
            isAuthenticated: false,
            user: null,
            sessionToken: null,
            accessToken: null,
            organizationId: null,
          });
          setGlobalAccessToken(null);
          setGlobalOrganizationId(null);
          return false;
        }
      },

      loginWithOAuth: async (returnUrl?: string): Promise<void> => {
        set({ isLoading: true, error: null });

        try {
          const baseUrl = window.location.origin;
          const successUrl = `${baseUrl}/api/auth/oauth/callback${
            returnUrl ? `?returnUrl=${encodeURIComponent(returnUrl)}` : ""
          }`;
          const failureUrl = `${baseUrl}/auth/login?error=oauth_failed`;

          const response = await fetch("/api/auth/oauth/initiate", {
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
        username: string;
        email: string;
        firstName: string;
        lastName: string;
        password: string;
      }): Promise<boolean> => {
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
          return true;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Registration failed";
          set({
            error: errorMessage,
            isLoading: false,
          });
          return false;
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
            sessionToken: null,
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
              sessionToken: null, // sessionToken is managed via cookies
              accessToken: data.accessToken,
              organizationId: data.user.organizationId ?? null,
            });

            setGlobalAccessToken(data.accessToken);
            setGlobalOrganizationId(data.user.organizationId ?? null);
          } else {
            set({
              user: null,
              isAuthenticated: false,
              sessionToken: null,
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
            sessionToken: null,
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
        sessionToken: state.sessionToken,
        accessToken: state.accessToken,
        organizationId: state.organizationId,
      }),
    }
  )
);
