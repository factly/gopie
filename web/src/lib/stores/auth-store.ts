import { create } from "zustand";
import { authClient } from "@/lib/auth/auth-client";
import {
  setGlobalOrganizationId,
} from "@/lib/api-client";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  emailVerified: boolean;
  image?: string | null;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  organizationId: string | null;
  role: string | null;

  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  loginWithOAuth: (returnUrl?: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (userData: {
    email: string;
    password: string;
    name: string;
  }) => Promise<{ success: boolean; error?: string }>;
  checkSession: () => Promise<void>;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  organizationId: null,
  role: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data, error } = await authClient.signIn.email({ email, password });
      if (error || !data) {
        throw new Error(error?.message || "Login failed");
      }
      // signIn.email returns { token, user } — fetch full session to get activeOrganizationId
      const { data: sessionData } = await authClient.getSession();
      const orgId = (sessionData?.session as { activeOrganizationId?: string } | undefined)?.activeOrganizationId ?? null;
      set({
        user: data.user as AuthUser,
        isAuthenticated: true,
        isLoading: false,
        organizationId: orgId,
      });
      setGlobalOrganizationId(orgId);
      return { success: true };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      set({ error: msg, isLoading: false, isAuthenticated: false, user: null });
      return { success: false, error: msg };
    }
  },

  loginWithOAuth: async (returnUrl?: string) => {
    set({ isLoading: true, error: null });
    try {
      await authClient.signIn.social({
        provider: "google",
        callbackURL: returnUrl ?? "/",
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "OAuth login failed";
      set({ error: msg, isLoading: false });
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await authClient.signOut();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        organizationId: null,
        isLoading: false,
        error: null,
      });
      setGlobalOrganizationId(null);
    }
  },

  register: async ({ email, password, name }) => {
    set({ isLoading: true, error: null });
    try {
      const { data, error } = await authClient.signUp.email({ email, password, name });
      if (error || !data) {
        throw new Error(error?.message || "Registration failed");
      }
      set({ isLoading: false });
      return { success: true };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      set({ error: msg, isLoading: false });
      return { success: false, error: msg };
    }
  },

  checkSession: async () => {
    try {
      const { data } = await authClient.getSession();
      if (data?.user && data?.session) {
        const orgId = (data.session as { activeOrganizationId?: string }).activeOrganizationId ?? null;
        set({
          user: data.user as AuthUser,
          isAuthenticated: true,
          organizationId: orgId,
          role: data.user.role
        });
        setGlobalOrganizationId(orgId);
      } else {
        set({ user: null, isAuthenticated: false, organizationId: null, role: null, });
        setGlobalOrganizationId(null);
      }
    } catch {
      set({ user: null, isAuthenticated: false, organizationId: null });
      setGlobalOrganizationId(null);
    }
  },

  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}));
