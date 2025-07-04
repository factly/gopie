"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Trash2Icon, DatabaseIcon, KeyIcon } from "lucide-react";
import { format } from "date-fns";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
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
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";

import { useDatabaseSources } from "@/lib/queries/secrets/list-database-sources";
import { useDeleteDatabaseSource } from "@/lib/mutations/secrets/delete-database-source";

export default function ManageSecretsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    data: databaseSources,
    isLoading,
    error,
  } = useDatabaseSources({
    variables: { limit: 100, page: 1 },
  });

  const deleteSourceMutation = useDeleteDatabaseSource({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-sources"] });
      toast({
        title: "Database source deleted",
        description: "The database source has been successfully removed.",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description:
          error.message ||
          "Failed to delete database source. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleDeleteSource = async (id: string) => {
    deleteSourceMutation.mutate({ id });
  };

  const maskConnectionString = (connectionString: string) => {
    try {
      const url = new URL(connectionString);
      if (url.password) {
        url.password = "****";
      }
      return url.toString();
    } catch {
      // If it's not a valid URL, just mask it generally
      return connectionString.replace(/(:)([^@:]*@)/g, "$1****@");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium">Manage Secrets</h3>
          <p className="text-sm text-muted-foreground">
            View and manage your saved database connection credentials.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyIcon className="h-5 w-5" />
              Database Sources
            </CardTitle>
            <CardDescription>
              Your saved database credentials and connection strings.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-1/3" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium">Manage Secrets</h3>
          <p className="text-sm text-muted-foreground">
            View and manage your saved database connection credentials.
          </p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4">
              <h4 className="text-sm font-semibold text-destructive">Error</h4>
              <p className="text-sm text-destructive/80 mt-1">
                {error.message}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const sources = databaseSources?.data || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div>
        <h3 className="text-lg font-medium">Manage Secrets</h3>
        <p className="text-sm text-muted-foreground">
          View and manage your saved database connection credentials.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyIcon className="h-5 w-5" />
            Database Sources
            <Badge variant="secondary" className="ml-2">
              {sources.length}
            </Badge>
          </CardTitle>
          <CardDescription>
            Your saved database credentials and connection strings.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sources.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-16 space-y-4"
            >
              <DatabaseIcon className="h-12 w-12 text-muted-foreground" />
              <div className="text-center space-y-2">
                <p className="text-base font-medium">
                  No database sources found
                </p>
                <p className="text-sm text-muted-foreground">
                  Database credentials will appear here when you create datasets
                  from database sources.
                </p>
              </div>
            </motion.div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Connection String</TableHead>
                    <TableHead>SQL Query</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sources.map((source, index) => (
                    <motion.tr
                      key={source.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="border-b transition-colors hover:bg-muted/50"
                    >
                      <TableCell className="font-medium">
                        <div className="max-w-[300px] truncate">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {maskConnectionString(source.connection_string)}
                          </code>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="max-w-[200px] truncate text-sm text-muted-foreground">
                          {source.sql_query}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(source.created_at), "MMM d, yyyy")}
                      </TableCell>
                      <TableCell>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                              disabled={deleteSourceMutation.isPending}
                            >
                              <Trash2Icon className="h-4 w-4" />
                              <span className="sr-only">Delete source</span>
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                Delete Database Source
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete this database
                                source? This action cannot be undone. The
                                connection string and associated data will be
                                permanently removed.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDeleteSource(source.id)}
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
    </motion.div>
  );
}
