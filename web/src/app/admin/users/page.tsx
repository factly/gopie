"use client";

import { useState, useEffect, useCallback } from "react";
import { authClient } from "@/lib/auth/auth-client";
import { validatePassword } from "@/lib/validation/password";
import { PasswordRules } from "@/components/auth/password-rules";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { MoreHorizontal, Plus, Search, Users } from "lucide-react";

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  banned: boolean | null;
  createdAt: Date;
  emailVerified: boolean;
}

type ConfirmAction =
  | { type: "ban"; user: AdminUser }
  | { type: "unban"; user: AdminUser }
  | { type: "remove"; user: AdminUser }
  | { type: "setRole"; user: AdminUser; role: "admin" | "user" };

const INITIAL_FORM = { name: "", email: "", password: "", role: "user" as "admin" | "user" };

export default function UsersPage() {
  const { data: session, isPending: sessionLoading } = authClient.useSession();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(INITIAL_FORM);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data, error: apiError } = await authClient.admin.listUsers({
        query: { limit: 100 },
      });
      if (apiError) {
        setError(apiError.message || "Failed to load users");
        return;
      }
      setUsers((data?.users ?? []) as AdminUser[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!sessionLoading) fetchUsers();
  }, [sessionLoading, fetchUsers]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    const { valid, errors } = validatePassword(createForm.password);
    if (!valid) {
      setCreateError(`Password must include: ${errors.join(", ").toLowerCase()}`);
      return;
    }

    setCreateLoading(true);
    try {
      const { data, error: apiError } = await authClient.admin.createUser({
        name: createForm.name,
        email: createForm.email,
        password: createForm.password,
        role: createForm.role,
      });
      if (apiError) {
        setCreateError(apiError.message || "Failed to create user");
        return;
      }
      // Add the new user as a member of the active organisation
      const orgId = (session?.session as { activeOrganizationId?: string } | undefined)
        ?.activeOrganizationId;
      if (orgId && data?.user?.id) {
        const res = await fetch("/api/auth/organization/add-member", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ userId: data.user.id, organizationId: orgId, role: "member" }),
          credentials: "include",
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          setCreateError(err.message || "User created but failed to add to organisation");
          await fetchUsers();
          return;
        }
      }
      setCreateOpen(false);
      setCreateForm(INITIAL_FORM);
      await fetchUsers();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreateLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    try {
      const { user } = confirmAction;
      if (confirmAction.type === "ban") {
        const { error: apiError } = await authClient.admin.banUser({ userId: user.id });
        if (apiError) throw new Error(apiError.message);
      } else if (confirmAction.type === "unban") {
        const { error: apiError } = await authClient.admin.unbanUser({ userId: user.id });
        if (apiError) throw new Error(apiError.message);
      } else if (confirmAction.type === "remove") {
        const { error: apiError } = await authClient.admin.removeUser({ userId: user.id });
        if (apiError) throw new Error(apiError.message);
      } else if (confirmAction.type === "setRole") {
        const { error: apiError } = await authClient.admin.setRole({
          userId: user.id,
          role: confirmAction.role,
        });
        if (apiError) throw new Error(apiError.message);
      }
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const confirmMeta: Record<string, { title: string; description: string; label: string; destructive: boolean }> = {
    ban: { title: "Ban user", description: "This will prevent the user from signing in.", label: "Ban", destructive: true },
    unban: { title: "Unban user", description: "This will restore the user's access.", label: "Unban", destructive: false },
    remove: { title: "Remove user", description: "This will permanently delete the user and all their data. This cannot be undone.", label: "Remove", destructive: true },
    setRole: { title: "Change role", description: `Set role to "${confirmAction?.type === "setRole" ? confirmAction.role : ""}" for this user.`, label: "Confirm", destructive: false },
  };

  return (
    <div className="w-full py-8 px-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6" />
          <div>
            <h1 className="text-2xl font-bold">Users</h1>
            <p className="text-muted-foreground text-sm">Manage all user accounts</p>
          </div>
        </div>
        <Button onClick={() => { setCreateForm(INITIAL_FORM); setCreateError(null); setCreateOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Create User
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search users..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <span className="text-sm text-muted-foreground ml-auto">
          {filteredUsers.length} user{filteredUsers.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredUsers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{user.name}</p>
                      <p className="text-sm text-muted-foreground">{user.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                      {user.role || "user"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {user.banned ? (
                      <Badge variant="destructive">Banned</Badge>
                    ) : user.emailVerified ? (
                      <Badge variant="outline">Active</Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground">Unverified</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(user.createdAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {user.id !== session?.user.id && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {user.role !== "admin" && (
                            <DropdownMenuItem onClick={() => setConfirmAction({ type: "setRole", user, role: "admin" as const })}>
                              Make admin
                            </DropdownMenuItem>
                          )}
                          {user.role === "admin" && (
                            <DropdownMenuItem onClick={() => setConfirmAction({ type: "setRole", user, role: "user" as const })}>
                              Remove admin
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          {user.banned ? (
                            <DropdownMenuItem onClick={() => setConfirmAction({ type: "unban", user })}>
                              Unban user
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem className="text-destructive" onClick={() => setConfirmAction({ type: "ban", user })}>
                              Ban user
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive" onClick={() => setConfirmAction({ type: "remove", user })}>
                            Remove user
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create User Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create User</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            {createError && (
              <Alert variant="destructive">
                <AlertDescription>{createError}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="create-name">Full Name</Label>
              <Input
                id="create-name"
                placeholder="John Doe"
                value={createForm.name}
                onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                disabled={createLoading}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-email">Email</Label>
              <Input
                id="create-email"
                type="email"
                placeholder="john@example.com"
                value={createForm.email}
                onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                disabled={createLoading}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-password">Password</Label>
              <Input
                id="create-password"
                type="password"
                placeholder="Enter a password"
                value={createForm.password}
                onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                disabled={createLoading}
                required
              />
              <PasswordRules password={createForm.password} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-role">Role</Label>
              <Select
                value={createForm.role}
                onValueChange={(v) => setCreateForm((f) => ({ ...f, role: v as "admin" | "user" }))}
                disabled={createLoading}
              >
                <SelectTrigger id="create-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} disabled={createLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={createLoading}>
                {createLoading ? "Creating..." : "Create User"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Confirm Action Dialog */}
      {confirmAction && (
        <AlertDialog open onOpenChange={(open) => !open && setConfirmAction(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{confirmMeta[confirmAction.type].title}</AlertDialogTitle>
              <AlertDialogDescription>
                <span className="font-medium">{confirmAction.user.name}</span>{" "}
                ({confirmAction.user.email})<br />
                {confirmMeta[confirmAction.type].description}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleConfirm}
                disabled={actionLoading}
                className={
                  confirmMeta[confirmAction.type].destructive
                    ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    : ""
                }
              >
                {actionLoading ? "Processing..." : confirmMeta[confirmAction.type].label}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
