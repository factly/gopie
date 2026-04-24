"use client";

import * as React from "react";
import { useState } from "react";
import { motion } from "framer-motion";
import { KeyIcon, PlusIcon, Trash2Icon, CopyIcon, CheckIcon, EyeIcon } from "lucide-react";
import { format } from "date-fns";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

import { useAPIKeys } from "@/lib/queries/apikeys/list-api-keys";
import { useCreateAPIKey, type CreateAPIKeyResponse } from "@/lib/mutations/apikeys/create-api-key";
import { useDeleteAPIKey } from "@/lib/mutations/apikeys/delete-api-key";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant="outline" size="sm" onClick={handleCopy} className="gap-1.5">
      {copied ? <CheckIcon className="h-3.5 w-3.5 text-green-500" /> : <CopyIcon className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

export default function APIKeysPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useAPIKeys({ variables: { limit: 50, page: 1 } });

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const [createdKey, setCreatedKey] = useState<CreateAPIKeyResponse | null>(null);

  const createMutation = useCreateAPIKey({
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setCreateOpen(false);
      setName("");
      setDescription("");
      setCreateError(null);
      setCreatedKey(data);
    },
    onError: (err) => {
      setCreateError(err.message || "Failed to create API key");
    },
  });

  const deleteMutation = useDeleteAPIKey({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      toast({ title: "API key deleted", description: "The API key has been permanently removed." });
    },
    onError: (err) => {
      toast({ title: "Error", description: err.message || "Failed to delete API key.", variant: "destructive" });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!name.trim()) {
      setCreateError("Name is required");
      return;
    }
    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined });
  };

  const keys = data?.results ?? [];

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">API Keys</h3>
        <p className="text-sm text-muted-foreground">
          Create and manage API keys for programmatic access to the Gopie API.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2">
              <KeyIcon className="h-5 w-5" />
              API Keys
              {!isLoading && (
                <Badge variant="secondary" className="ml-1">{keys.length}</Badge>
              )}
            </CardTitle>
            <CardDescription>
              Keys are shown only once at creation. Store them securely.
            </CardDescription>
          </div>
          <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
            <PlusIcon className="h-4 w-4" />
            New Key
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-4 border">
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-1/4" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                  <Skeleton className="h-8 w-8" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="border border-destructive/50 bg-destructive/5 p-4">
              <p className="text-sm text-destructive">{error.message}</p>
            </div>
          ) : keys.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-16 space-y-4"
            >
              <KeyIcon className="h-12 w-12 text-muted-foreground" />
              <div className="text-center space-y-2">
                <p className="text-base font-medium">No API keys yet</p>
                <p className="text-sm text-muted-foreground">
                  Create an API key to access the Gopie API programmatically.
                </p>
              </div>
              <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
                <PlusIcon className="h-4 w-4" />
                New Key
              </Button>
            </motion.div>
          ) : (
            <div className="border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-[60px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.map((key, index) => (
                    <motion.tr
                      key={key.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="border-b transition-colors hover:bg-muted/50"
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          {key.name}
                          {key.is_revoked && <Badge variant="destructive" className="text-xs">Revoked</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                        {key.description || "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {key.last_used_at ? format(new Date(key.last_used_at), "MMM d, yyyy") : "Never"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(key.created_at), "MMM d, yyyy")}
                      </TableCell>
                      <TableCell>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                              disabled={deleteMutation.isPending}
                            >
                              <Trash2Icon className="h-4 w-4" />
                              <span className="sr-only">Delete key</span>
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete API Key</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete <strong>{key.name}</strong>? Any applications using this key will lose access immediately. This cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => deleteMutation.mutate({ id: key.id })}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </TableCell>
                    </motion.tr>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) { setName(""); setDescription(""); setCreateError(null); } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Give your key a name so you can identify it later.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="key-name">Name <span className="text-destructive">*</span></Label>
              <Input
                id="key-name"
                placeholder="e.g. Production, CI/CD"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="key-desc">Description</Label>
              <Input
                id="key-desc"
                placeholder="Optional description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            {createError && (
              <p className="text-sm text-destructive">{createError}</p>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Key"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* One-time key reveal dialog */}
      <Dialog open={!!createdKey} onOpenChange={(open) => { if (!open) setCreatedKey(null); }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <EyeIcon className="h-5 w-5 text-amber-500" />
              Save Your API Key
            </DialogTitle>
            <DialogDescription>
              This is the only time your key will be shown. Copy it now and store it somewhere safe — you will not be able to see it again.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Key name</Label>
              <p className="font-medium">{createdKey?.apikey.name}</p>
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">API Key</Label>
              <div className="flex items-center gap-2">
                <code className="flex-1 block p-3 bg-muted rounded font-mono text-sm break-all select-all">
                  {createdKey?.key}
                </code>
                {createdKey?.key && <CopyButton text={createdKey.key} />}
              </div>
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-3">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Store this key securely. If you lose it you will need to create a new one.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setCreatedKey(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
