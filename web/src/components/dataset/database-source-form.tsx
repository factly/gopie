"use client";

import * as React from "react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, Loader2 } from "lucide-react";
import { useSourceDatabaseDatasetSSE } from "@/lib/mutations/dataset/source-database-dataset";
import { Progress } from "@/components/ui/progress";
import { SSEEvent } from "@/lib/sse-client";
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
  onSuccess: (datasetAlias: string, datasetId: string) => void;
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
  const [customPrompt, setCustomPrompt] = useState("");
  const [connectionString, setConnectionString] = useState("");
  const [sqlQuery, setSqlQuery] = useState("");
  const [timestampColumn, setTimestampColumn] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  
  // Progress State for Dialog UI
  const [uploadProgress, setUploadProgress] = useState<{
    message: string;
    percentage: number;
  } | null>(null);

  const startDatabaseUpload = useSourceDatabaseDatasetSSE();

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

    // Initialize Progress
    let currentProgress = 0;
    setUploadProgress({ message: "Initializing connection...", percentage: 0 });

    try {
      const response = await startDatabaseUpload({
        alias: datasetAlias,
        description: datasetDescription.trim() || undefined,
        custom_prompt: customPrompt.trim() || undefined,
        connection_string: connectionString,
        sql_query: sqlQuery,
        driver,
        project_id: projectId,
        created_by: "system",
        timestamp_column: timestampColumn,
        onProgress: (event: SSEEvent) => {
          if (event.type === 'status_update') {
            currentProgress = Math.min(currentProgress + 10, 90);
            setUploadProgress({
              message: event.message,
              percentage: currentProgress
            });
          }
        }
      });

      // Handle both response structures
      const result = (response as unknown as Record<string, unknown>)?.data || response;
      
      // Type the result properly
      const typedResult = result as Record<string, unknown>;
      const dataset = typedResult?.dataset as Record<string, unknown> | undefined;
      
      if (!dataset?.id) {
        const errMessage = "Invalid response from server: Dataset ID not found.";
        setFormError(errMessage);
        onError(errMessage);
        setUploadProgress(null); // Reset UI on error so user can fix
        return;
      }
      
      // Success will close the dialog via the parent callback
      onSuccess(dataset.alias as string, dataset.id as string);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
      setFormError(errorMessage);
      setUploadProgress(null); // Reset UI to show form again
      // We don't call onError here to keep the dialog open so user can retry
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>
          Add Dataset from {driver === "postgres" ? "PostgreSQL" : "MySQL"}
        </DialogTitle>
        <DialogDescription>
          {uploadProgress 
            ? "Creating your dataset. Please wait while we process the data..."
            : "Provide connection details and a SQL query to create a new dataset."
          }
        </DialogDescription>
      </DialogHeader>

      {formError && !uploadProgress && (
        <Alert variant="destructive" className="my-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      {uploadProgress ? (
        // PROGRESS UI
        <div className="py-8 space-y-6">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="font-medium text-foreground">
                  {uploadProgress.message}
                </span>
              </div>
              <span className="text-muted-foreground">
                {uploadProgress.percentage}%
              </span>
            </div>
            <Progress value={uploadProgress.percentage} className="h-2" />
          </div>
          <p className="text-xs text-muted-foreground text-center">
            This process may take a minute depending on the size of your query.
          </p>
        </div>
      ) : (
        // FORM UI
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
           <div>
            <Label htmlFor="timestampColumn">Timestamp column</Label>
            <Input
              id="timestampColumn"
              value={timestampColumn}
              onChange={(e) => setTimestampColumn(e.target.value)}
              placeholder="e.g., updated_at"
            />
          </div>
          <div>
            <Label htmlFor="customPrompt">Custom Prompt (Optional)</Label>
            <Textarea
              id="customPrompt"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Enter a custom prompt to guide AI interactions with this dataset..."
              rows={3}
            />
          </div>
          <DialogFooter className="pt-4">
            <DialogClose asChild>
              <Button type="button" variant="outline" onClick={onCloseDialog}>
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit">
              Create Dataset
            </Button>
          </DialogFooter>
        </form>
      )}
    </>
  );
}