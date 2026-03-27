import { useAuthStore } from "@/lib/stores/auth-store";

export interface PermissionCheck {
  canRead: boolean;
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  isAdmin: boolean;
  role: string | null;
}

/**
 * Hook to check user permissions based on user role (from better-auth admin plugin).
 * Uses the global user role ("admin" | "user"), not the org membership role.
 *
 * Access Matrix:
 * - user: Create, Read, Edit, Delete - only user projects but can read all projects
 * - admin: Create, Read, Edit, Delete
 */
export function usePermissions(): PermissionCheck {
  const { role } = useAuthStore();
  const isAuthDisabled = String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() !== "true";

  const effectiveRole = isAuthDisabled ? "admin" : role;

  const isAdmin = effectiveRole === "admin";

  return {
    canRead: true,
    canCreate: isAdmin,
    canEdit: isAdmin,
    canDelete: isAdmin,
    isAdmin,
    role: effectiveRole,
  };
}

/**
 * Hook to check if user has permissions for a specific resource
 * Combines role-based permissions with creator ownership
 *
 * @param createdBy - The user ID of the resource creator
 * @returns Permission checks including creator-specific permissions
 */
export function useResourcePermissions(createdBy?: string | null): PermissionCheck & {
  isCreator: boolean;
} {
  const { user } = useAuthStore();
  const permissions = usePermissions();

  const isCreator = !!createdBy && user?.id === createdBy;

  return {
    ...permissions,
    canEdit: permissions.canEdit || isCreator,
    canDelete: permissions.canDelete || isCreator,
    isCreator,
  };
}