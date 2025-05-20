"use client";

import * as React from "react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { useSourceDatabaseDataset } from "@/lib/mutations/dataset/source-database-dataset";
import {
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";

interface DatabaseSourceFormProps {
  projectId: string;
  driver: "postgres" | "mysql";
  onCloseDialog: () => void;
  onSuccess: (datasetAlias: string) => void;
  onError: (errorMessage: string) => void;
}

export function DatabaseSourceForm({
  projectId,
  driver,
  onCloseDialog,
  onSuccess,
  onError,
}: DatabaseSourceFormProps) {
  const [datasetAlias, setDatasetAlias] = useState("");
  const [datasetDescription, setDatasetDescription] = useState("");
  const [connectionString, setConnectionString] = useState("");
  const [sqlQuery, setSqlQuery] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const sourceDatabaseDataset = useSourceDatabaseDataset();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!datasetAlias.trim()) {
      setFormError("Dataset Name (Alias) is required.");
      return;
    }
    if (!connectionString.trim()) {
      setFormError("Connection String is required.");
      return;
    }
    if (!sqlQuery.trim()) {
      setFormError("SQL Query is required.");
      return;
    }

    try {
      const result = await sourceDatabaseDataset.mutateAsync({
        alias: datasetAlias,
        description: datasetDescription.trim() || undefined,
        connection_string: connectionString,
        sql_query: sqlQuery,
        driver,
        project_id: projectId,
        created_by: "system",
      });

      if (!result?.dataset?.id) {
        const errMessage =
          "Invalid response from server: Dataset ID not found.";
        setFormError(errMessage);
        onError(errMessage);
        return;
      }
      onSuccess(result.dataset.alias);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An unknown error occurred.";
      setFormError(errorMessage);
      onError(errorMessage);
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>
          Add Dataset from {driver === "postgres" ? "PostgreSQL" : "MySQL"}
        </DialogTitle>
        <DialogDescription>
          Provide connection details and a SQL query to create a new dataset.
        </DialogDescription>
      </DialogHeader>
      {formError && (
        <Alert variant="destructive" className="my-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Validation Error</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={handleSubmit} className="space-y-4 py-4">
        <div>
          <Label htmlFor="datasetAlias">Dataset Name (Alias)</Label>
          <Input
            id="datasetAlias"
            value={datasetAlias}
            onChange={(e) => setDatasetAlias(e.target.value)}
            placeholder="e.g., customer_orders_2024"
            required
          />
        </div>
        <div>
          <Label htmlFor="datasetDescription">
            Dataset Description (Optional)
          </Label>
          <Textarea
            id="datasetDescription"
            value={datasetDescription}
            onChange={(e) => setDatasetDescription(e.target.value)}
            placeholder="e.g., All customer orders from the Q1 2024"
          />
        </div>
        <div>
          <Label htmlFor="connectionString">Connection String</Label>
          <Input
            id="connectionString"
            type="password"
            value={connectionString}
            onChange={(e) => setConnectionString(e.target.value)}
            placeholder={
              driver === "postgres"
                ? "postgresql://user:password@host:port/database"
                : "mysql://user:password@host:port/database"
            }
            required
          />
        </div>
        <div>
          <Label htmlFor="sqlQuery">SQL Query</Label>
          <Textarea
            id="sqlQuery"
            value={sqlQuery}
            onChange={(e) => setSqlQuery(e.target.value)}
            placeholder="SELECT id, name, order_date FROM orders WHERE order_date > '2024-01-01';"
            rows={5}
            required
          />
        </div>
        <DialogFooter className="pt-4">
          <DialogClose asChild>
            <Button type="button" variant="outline" onClick={onCloseDialog}>
              Cancel
            </Button>
          </DialogClose>
          <Button type="submit" disabled={sourceDatabaseDataset.isPending}>
            {sourceDatabaseDataset.isPending ? "Creating..." : "Create Dataset"}
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}
