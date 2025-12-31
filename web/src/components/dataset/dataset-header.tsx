import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  DownloadIcon,
  PencilIcon,
  CheckIcon,
  XIcon,
  MessageSquareIcon,
  DatabaseIcon,
  TableIcon,
  RowsIcon,
  ClockIcon,
  InfoIcon,
  UserIcon,
  CodeIcon,
  FileText,
  Loader2Icon,
  CheckCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  RefreshCwIcon, 
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { updateDataset } from "@/lib/mutations/dataset/update-dataset";
import { Dataset } from "@/lib/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { Textarea } from "@/components/ui/textarea";
import { useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { ColumnDescriptionsModal } from "@/components/dataset/column-descriptions-modal";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateDownload } from "@/lib/mutations/download/create-download";
import { useDownloadStore } from "@/lib/stores/download-store";
import { Progress } from "@/components/ui/progress";
import { format as formatSQL } from "sql-formatter";
import { useRefreshDatabaseDataset } from "@/lib/mutations/dataset/refresh-dataset-database";
import { useCheckTimestampColumn } from "@/lib/queries/dataset/check-timestamp-column";
// Dynamically import Monaco Editor to avoid SSR issues
const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="min-h-[150px] flex items-center justify-center border rounded-md bg-muted/20">
      <Loader2Icon className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  ),
});

interface DatasetHeaderProps {
  dataset: Dataset;
  projectId: string;
  onUpdate?: () => Promise<void>;
}

// Helper function to format SQL queries safely
function formatSqlQuery(sql: string): string {
  try {
    return formatSQL(sql, {
      language: "sql",
      tabWidth: 2,
      useTabs: false,
      keywordCase: "upper",
      linesBetweenQueries: 2,
    });
  } catch (error) {
    console.error("Failed to format SQL:", error);
    return sql; // Return original SQL if formatting fails
  }
}

// Helper function to determine dataset source (commented out as unused)
/*
function getDatasetSource(dataset: Dataset): string {
  // Check if dataset was sourced from database
  if (
    dataset.description?.includes("Dataset sourced from database via GoPie Web")
  ) {
    // Try to determine specific database from description or file path
    if (
      dataset.description.toLowerCase().includes("postgres") ||
      dataset.file_path?.toLowerCase().includes("postgres")
    ) {
      return "PostgreSQL";
    }
    if (
      dataset.description.toLowerCase().includes("mysql") ||
      dataset.file_path?.toLowerCase().includes("mysql")
    ) {
      return "MySQL";
    }
    // Generic database if we can't determine specific type
    return "Database";
  }

  // Check if it's a file upload (S3 path)
  if (dataset.file_path?.startsWith("s3:/")) {
    // Return the actual file format
    const format = dataset.format?.toLowerCase();
    switch (format) {
      case "csv":
        return "CSV";
      case "parquet":
        return "Parquet";
      case "json":
        return "JSON";
      case "excel":
        return "Excel";
      case "duckdb":
        return "DuckDB";
      default:
        return dataset.format || "File";
    }
  }

  // Fallback to format if we can't determine source
  return dataset.format || "Unknown";
}
*/

export function DatasetHeader({
  dataset,
  projectId,
  onUpdate,
}: DatasetHeaderProps) {
  const { toast } = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { resolvedTheme } = useTheme();
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [editedAlias, setEditedAlias] = useState(dataset.alias || "");
  const [editedDescription, setEditedDescription] = useState(
    dataset.description || ""
  );
  const [editedCustomPrompt, setEditedCustomPrompt] = useState(
    dataset.custom_prompt || ""
  );
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);

  // Download state
  const [isDownloadDialogOpen, setIsDownloadDialogOpen] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState<
    "csv" | "json" | "parquet"
  >("csv");
  const [downloadSql, setDownloadSql] = useState(
    formatSqlQuery(`SELECT * FROM "${dataset.name}"`)
  );
  const [completedDownloadUrl, setCompletedDownloadUrl] = useState<
    string | null
  >(null);
  const { createDownload } = useCreateDownload();
  const { currentDownloadProgress, setCurrentDownloadProgress } =
    useDownloadStore();

  // DB Refresh state
  const [isDbRefreshDialogOpen, setIsDbRefreshDialogOpen] = useState(false);
  const [isDbRefreshing, setIsDbRefreshing] = useState<
    "partial" | "full" | null
  >(null);

  // Instantiate the mutation hook
  const { mutateAsync: refreshDbDataset } = useRefreshDatabaseDataset();
  const { data: hasTimestampColumn, isLoading: isLoadingTimestampCheck } =
  useCheckTimestampColumn({
    variables: { datasetId: dataset.id }, 
    enabled: dataset.source === "database",
  });
  
 const canIncrementalRefresh = hasTimestampColumn === true;


  const handleUpdate = async () => {
    if (editedDescription.length < 10) {
      toast({
        title: "Validation Error",
        description: "Description must be at least 10 characters long.",
        variant: "destructive",
      });
      return;
    }

    setIsUpdating(true);
    try {
      await updateDataset(projectId, dataset.id, {
        alias: editedAlias,
        description: editedDescription,
        custom_prompt: editedCustomPrompt,
        updated_by: "gopie-web-ui",
      });

      await queryClient.invalidateQueries({
        queryKey: ["dataset", { projectId, datasetId: dataset.id }],
      });

      await queryClient.invalidateQueries({
        queryKey: ["datasets"],
      });

      if (onUpdate) {
        await onUpdate();
      }

      setIsEditing(false);
      toast({
        title: "Dataset updated",
        description: "The dataset has been updated successfully.",
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to update dataset";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCancel = () => {
    setEditedAlias(dataset.alias || "");
    setEditedDescription(dataset.description || "");
    setEditedCustomPrompt(dataset.custom_prompt || "");
    setIsEditing(false);
  };

  const handleChatClick = () => {
    const contextData = encodeURIComponent(
      JSON.stringify([
        {
          id: dataset.id,
          type: "dataset",
          name: dataset.alias || dataset.name,
          projectId: projectId,
        },
      ])
    );

    router.push(`/chat?contextData=${contextData}`);
  };

  const handleDownload = async () => {
    // If we have a completed download URL, just open it
    if (completedDownloadUrl) {
      window.open(completedDownloadUrl, "_blank");
      return;
    }

    try {
      const result = await createDownload({
        dataset_id: dataset.id,
        sql: downloadSql,
        format: downloadFormat,
      });

      // Store the completed URL for re-download
      if (result.url) {
        setCompletedDownloadUrl(result.url);
        // Automatically open the download URL in a new tab
        window.open(result.url, "_blank");
      }

      toast({
        title: "Download ready",
        description: "Your download has been prepared and opened in a new tab.",
      });

      // Don't close the dialog, just update the state to show completion
      // User can close manually or download again
    } catch (error) {
      toast({
        title: "Download failed",
        description:
          error instanceof Error ? error.message : "Failed to create download",
        variant: "destructive",
      });
      setCompletedDownloadUrl(null);
    }
  };

  const handleDbRefresh = async (type: "partial" | "full") => {
    setIsDbRefreshing(type); // Set UI loading state
    toast({
      title: "Refresh Started",
      description: `Starting ${type} refresh...`,
    });

    // Translate "partial" to "incremental" for the API
    const apiRefreshType = type === "partial" ? "incremental" : "full";

    try {
      await refreshDbDataset({
        projectId: projectId,
        datasetName: dataset.name, // Use the real table name
        refreshType: apiRefreshType,
      });

      toast({
        title: "Refresh Successful",
        description: `Dataset ${type} refresh completed.`,
      });

      // Invalidate queries to update data
      await queryClient.invalidateQueries({
        queryKey: ["dataset", { projectId, datasetId: dataset.id }],
      });
      await queryClient.invalidateQueries({
        queryKey: ["datasets"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["get-schema", dataset.id],
      });

      await queryClient.invalidateQueries({
        queryKey: ["get-table"],
      });

      setIsDbRefreshDialogOpen(false); // Close dialog if it was open
    } catch (err) {
      const error = err as Error;
      toast({
        title: "Refresh Failed",
        description: error.message || "An unknown error occurred.",
        variant: "destructive",
      });
    } finally {
      setIsDbRefreshing(null); // Clear UI loading state
    }
  };

  // Reset download progress and URL when dialog closes, format SQL when dialog opens
  useEffect(() => {
    if (!isDownloadDialogOpen) {
      setCurrentDownloadProgress(null);
      setCompletedDownloadUrl(null);
    } else {
      // Format the SQL when dialog opens
      setDownloadSql(formatSqlQuery(`SELECT * FROM "${dataset.name}"`));
    }
  }, [isDownloadDialogOpen, setCurrentDownloadProgress, dataset.name]);

  return (
    <div className="space-y-6">
      {/* Main Header */}
      <div className="flex items-start gap-6 relative">
        <div className="absolute -top-8 -right-8 w-[50px] h-[50px] bg-gradient-to-br from-primary/10 to-primary/5 transition-all duration-300 ease-in-out opacity-100" />
        {/* Chat Button */}
        <Button
          variant="ghost"
          size="sm"
          className="absolute -top-8 -right-8 h-[50px] w-[50px] p-0 z-10"
          title="Chat with Dataset"
          onClick={handleChatClick}
        >
          <MessageSquareIcon className="h-4 w-4" />
        </Button>

        {/* Left Section - Main Info */}
        <div className="flex items-start gap-4 flex-1 min-w-0 pr-[10px]">
          <div className="flex-1 min-w-0 space-y-3">
            {isEditing ? (
              <div className="space-y-4 animate-in fade-in">
                {/* Name Section with Buttons */}
                <div className="flex items-end gap-3">
                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      Dataset Name
                    </label>
                    <Input
                      value={editedAlias}
                      onChange={(e) => setEditedAlias(e.target.value)}
                      className="font-semibold text-lg h-10"
                      placeholder="Enter a friendly name..."
                      autoFocus
                    />
                  </div>
                  <div className="flex items-center gap-2 pb-0.5">
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleUpdate}
                      disabled={isUpdating}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCancel}
                      disabled={isUpdating}
                    >
                      <XIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
                {/* Description Section */}
                <div className="space-y-2">
                  <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                    Description
                  </label>
                  <Textarea
                    value={editedDescription}
                    onChange={(e) => setEditedDescription(e.target.value)}
                    className="resize-none min-h-[100px]"
                    placeholder="Enter a description..."
                    rows={4}
                  />
                </div>
                {/* Custom Prompt Section */}
                <div className="space-y-2">
                  <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                    Custom Prompt
                  </label>
                  <Textarea
                    value={editedCustomPrompt}
                    onChange={(e) => setEditedCustomPrompt(e.target.value)}
                    className="resize-none min-h-[80px]"
                    placeholder="Enter a custom prompt to guide AI interactions with this dataset..."
                    rows={3}
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-foreground truncate">
                    {dataset.alias || "Untitled Dataset"}
                  </h1>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 hover:bg-secondary/80 flex-shrink-0"
                    onClick={() => setIsEditing(true)}
                  >
                    <PencilIcon className="h-4 w-4" />
                  </Button>
                </div>

                {/* Description */}
                <div className="group">
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      {dataset.description &&
                      dataset.description.length > 200 ? (
                        isDescriptionExpanded ? (
                          <div className="text-muted-foreground leading-relaxed">
                            <span>{dataset.description}</span>{" "}
                            <Button
                              variant="link"
                              size="sm"
                              className="h-auto p-0 text-primary hover:text-primary/80 font-medium inline-flex items-center align-baseline"
                              onClick={() => setIsDescriptionExpanded(false)}
                            >
                              <ChevronUpIcon className="h-3 w-3 mr-0.5" />
                              Less
                            </Button>
                          </div>
                        ) : (
                          <div className="text-muted-foreground leading-relaxed">
                            <p className="line-clamp-2 mb-1">
                              {dataset.description}
                            </p>
                            <Button
                              variant="link"
                              size="sm"
                              className="h-auto p-0 text-primary hover:text-primary/80 font-medium inline-flex items-center"
                              onClick={() => setIsDescriptionExpanded(true)}
                            >
                              <ChevronDownIcon className="h-3 w-3 mr-0.5" />
                              More
                            </Button>
                          </div>
                        )
                      ) : (
                        <p className="text-muted-foreground leading-relaxed">
                          {dataset.description || "No description provided"}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 hover:bg-secondary/80 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                      onClick={() => setIsEditing(true)}
                    >
                      <PencilIcon className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                {/* Custom Prompt */}
                {dataset.custom_prompt && (
                  <div className="group">
                    <div className="flex items-start gap-2">
                      <div className="flex-1 pr-8">
                        <p className="text-sm font-medium text-muted-foreground mb-1">
                          Custom Prompt:
                        </p>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {dataset.custom_prompt}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 hover:bg-secondary/80 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                        onClick={() => setIsEditing(true)}
                      >
                        <PencilIcon className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                )}

                {/* Quick Stats */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 text-sm">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-4">
                    <div className="flex items-center gap-2">
                      <TableIcon className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">
                        {new Intl.NumberFormat("en", {
                          notation: "compact",
                        }).format(dataset.row_count || 0)}
                      </span>
                      <span className="text-muted-foreground">rows</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <RowsIcon className="h-4 w-4 text-muted-foreground rotate-90" />
                      <span className="font-medium">
                        {dataset.columns?.length || 0}
                      </span>
                      <span className="text-muted-foreground">columns</span>
                    </div>
                    <ColumnDescriptionsModal
                      datasetId={dataset.id}
                      datasetName={dataset.alias || dataset.name}
                      trigger={
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-muted-foreground hover:text-foreground inline-flex"
                          title="Column Descriptions"
                        >
                          <FileText className="h-4 w-4 sm:mr-1" />
                          <span className="hidden sm:inline lg:hidden">Columns</span>
                          <span className="hidden lg:inline">Column Descriptions</span>
                        </Button>
                      }
                    />
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-muted-foreground hover:text-foreground"
                          title="More details"
                        >
                          <InfoIcon className="h-4 w-4 sm:mr-1" />
                          <span className="hidden sm:inline">More details</span>
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-md">
                        <DialogHeader>
                          <DialogTitle>Dataset Details</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          {/* Basic Stats */}
                          <div className="space-y-3">
                            <h4 className="font-medium text-sm">Statistics</h4>
                            <div className="grid grid-cols-2 gap-3">
                              <div className="bg-secondary/20 p-3">
                                <div className="text-xs text-muted-foreground mb-1">
                                  Rows
                                </div>
                                <div className="font-semibold">
                                  {new Intl.NumberFormat("en", {
                                    notation: "compact",
                                  }).format(dataset.row_count || 0)}
                                </div>
                              </div>
                              <div className="bg-secondary/20 p-3">
                                <div className="text-xs text-muted-foreground mb-1">
                                  Columns
                                </div>
                                <div className="font-semibold">
                                  {dataset.columns?.length || 0}
                                </div>
                              </div>
                              <div className="bg-secondary/20 p-3 col-span-2">
                                <div className="text-xs text-muted-foreground mb-1">
                                  File Size
                                </div>
                                <div className="font-semibold">
                                  {dataset.size
                                    ? `${(dataset.size / (1024 * 1024)).toFixed(
                                        1
                                      )} MB`
                                    : "N/A"}
                                </div>
                              </div>
                            </div>
                          </div>

                          <Separator />

                          {/* Timestamps */}
                          <div className="space-y-3">
                            <h4 className="font-medium text-sm">Timeline</h4>
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm">
                                <ClockIcon className="h-4 w-4 text-muted-foreground" />
                                <span className="text-muted-foreground">
                                  Created:
                                </span>
                                <span className="font-medium">
                                  {format(
                                    new Date(dataset.created_at),
                                    "MMM d, yyyy 'at' h:mm a"
                                  )}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 text-sm">
                                <ClockIcon className="h-4 w-4 text-muted-foreground" />
                                <span className="text-muted-foreground">
                                  Updated:
                                </span>
                                <span className="font-medium">
                                  {format(
                                    new Date(dataset.updated_at),
                                    "MMM d, yyyy 'at' h:mm a"
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>

                          <Separator />

                          {/* Contributors */}
                          <div className="space-y-3">
                            <h4 className="font-medium text-sm">
                              Contributors
                            </h4>
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm">
                                <UserIcon className="h-4 w-4 text-muted-foreground" />
                                <span className="text-muted-foreground">
                                  Created by:
                                </span>
                                <span className="font-medium">
                                  {dataset.created_by}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 text-sm">
                                <UserIcon className="h-4 w-4 text-muted-foreground" />
                                <span className="text-muted-foreground">
                                  Updated by:
                                </span>
                                <span className="font-medium">
                                  {dataset.updated_by}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>

                  {/* Action Buttons */}
                  {!isEditing && (
                    <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                      <Dialog
                        open={isDownloadDialogOpen}
                        onOpenChange={setIsDownloadDialogOpen}
                      >
                        <DialogTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                            title="Download Dataset"
                          >
                            <DownloadIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[600px]">
                          <DialogHeader>
                            <DialogTitle>Download Dataset</DialogTitle>
                            <DialogDescription>
                              Export your dataset in your preferred format
                            </DialogDescription>
                          </DialogHeader>
                          <div className="space-y-4 py-4">
                            <div className="space-y-2">
                              <label className="text-sm font-medium">
                                Format
                              </label>
                              <Select
                                value={downloadFormat}
                                onValueChange={(value) =>
                                  setDownloadFormat(
                                    value as "csv" | "json" | "parquet"
                                  )
                                }
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="csv">
                                    CSV - Comma-separated values
                                  </SelectItem>
                                  <SelectItem value="json">
                                    JSON - JavaScript Object Notation
                                  </SelectItem>
                                  <SelectItem value="parquet">
                                    Parquet - Columnar storage format
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <label className="text-sm font-medium">
                                  SQL Query
                                </label>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    const formatted =
                                      formatSqlQuery(downloadSql);
                                    setDownloadSql(formatted);
                                  }}
                                  className="h-7 text-xs"
                                >
                                  Format SQL
                                </Button>
                              </div>
                              <div className="border rounded-md overflow-hidden">
                                <Editor
                                  height="150px"
                                  defaultLanguage="sql"
                                  value={downloadSql}
                                  onChange={(value) =>
                                    setDownloadSql(value || "")
                                  }
                                  theme={
                                    resolvedTheme === "dark"
                                      ? "vs-dark"
                                      : "light"
                                  }
                                  options={{
                                    minimap: { enabled: false },
                                    fontSize: 13,
                                    lineNumbers: "on",
                                    roundedSelection: false,
                                    scrollBeyondLastLine: false,
                                    automaticLayout: true,
                                    wordWrap: "on",
                                    wrappingIndent: "indent",
                                    formatOnPaste: true,
                                    formatOnType: true,
                                    scrollbar: {
                                      vertical: "auto",
                                      horizontal: "auto",
                                    },
                                    padding: {
                                      top: 8,
                                      bottom: 8,
                                    },
                                  }}
                                />
                              </div>
                              <p className="text-xs text-muted-foreground">
                                Customize the SQL query to filter or transform
                                your data before download
                              </p>
                            </div>
                            {currentDownloadProgress && (
                              <div className="space-y-2">
                                <div className="flex items-center justify-between text-sm">
                                  <span className="text-muted-foreground">
                                    {currentDownloadProgress.message}
                                  </span>
                                  <span className="font-medium">
                                    {currentDownloadProgress.progress}%
                                  </span>
                                </div>
                                <Progress
                                  value={currentDownloadProgress.progress}
                                />
                              </div>
                            )}
                            {completedDownloadUrl &&
                              !currentDownloadProgress && (
                                <div className="rounded-lg bg-green-50 dark:bg-green-950 p-3 text-sm text-green-800 dark:text-green-200">
                                  <div className="flex items-center gap-2">
                                    <CheckCircleIcon className="h-4 w-4" />
                                    <span>
                                      Download completed successfully! The file
                                      has been opened in a new tab.
                                    </span>
                                  </div>
                                </div>
                              )}
                          </div>
                          <DialogFooter>
                            <Button
                              variant="outline"
                              onClick={() => {
                                setIsDownloadDialogOpen(false);
                                setCompletedDownloadUrl(null);
                              }}
                              disabled={
                                currentDownloadProgress?.status === "processing"
                              }
                            >
                              {completedDownloadUrl ? "Close" : "Cancel"}
                            </Button>
                            <Button
                              onClick={handleDownload}
                              disabled={
                                !downloadSql ||
                                currentDownloadProgress?.status === "processing"
                              }
                            >
                              {currentDownloadProgress?.status ===
                              "processing" ? (
                                <>
                                  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                                  Processing...
                                </>
                              ) : completedDownloadUrl ? (
                                <>
                                  <DownloadIcon className="mr-2 h-4 w-4" />
                                  Download File
                                </>
                              ) : (
                                <>
                                  <DownloadIcon className="mr-2 h-4 w-4" />
                                  Download
                                </>
                              )}
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                      <Link
                        href={`/projects/${projectId}/datasets/${dataset.id}/data/`}
                      >
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                          title="Query Dataset"
                        >
                          <DatabaseIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                        </Button>
                      </Link>
                      <Link
                        href={`/projects/${projectId}/datasets/${dataset.id}/api`}
                      >
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                          title="API Playground"
                        >
                          <CodeIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                        </Button>
                      </Link>
                      {/* File source: always navigate */}
                      {dataset.source === "file" && (
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                          title="Refresh Dataset"
                          onClick={() =>
                            router.push(
                              `/projects/${projectId}/datasets/${dataset.id}/refresh`
                            )
                          }
                          disabled={!!isDbRefreshing} // Disable if a DB refresh is happening
                        >
                          <RefreshCwIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                        </Button>
                      )}

                      {/* DB source: check if incremental is possible */}
{dataset.source === "database" && (
                        <>
                          {/* Show a loader while checking for timestamp column */}
                          {isLoadingTimestampCheck ? (
                            <Button
                              variant="outline"
                              size="icon"
                              className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                              title="Checking refresh options..."
                              disabled
                            >
                              <Loader2Icon className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                            </Button>
                          ) : canIncrementalRefresh ? (
                            /* If incremental is possible, show dialog with options */
                            <Dialog
                              open={isDbRefreshDialogOpen}
                              onOpenChange={setIsDbRefreshDialogOpen}
                            >
                              <DialogTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="icon"
                                  className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                                  title="Refresh Dataset"
                                  disabled={!!isDbRefreshing} // Disable trigger if a refresh is in progress
                                >
                                  {isDbRefreshing ? (
                                    <Loader2Icon className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                                  ) : (
                                    <RefreshCwIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                                  )}
                                </Button>
                              </DialogTrigger>
                              <DialogContent className="sm:max-w-md">
                                <DialogHeader>
                                  <DialogTitle>
                                    Refresh Dataset
                                  </DialogTitle>
                                  <DialogDescription>
                                    Choose the type of refresh to perform. This
                                    will pull the latest data from the source
                                    database.
                                  </DialogDescription>
                                </DialogHeader>
                                <div className="flex flex-row space-x-3 py-4">
                                  <Button
                                    className="flex-1 justify-center gap-2 font-medium"
                                    onClick={() => handleDbRefresh("partial")}
                                    disabled={!!isDbRefreshing}
                                  >
                                    {isDbRefreshing === "partial" ? (
                                      <Loader2Icon className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <RefreshCwIcon className="h-4 w-4" />
                                    )}
                                    <span className="inline-block min-w-[150px] text-center">
                                      Incremental Refresh
                                    </span>
                                  </Button>

                                  <Button
                                    className="flex-1 justify-center gap-2 font-medium"
                                    variant="destructive"
                                    onClick={() => handleDbRefresh("full")}
                                    disabled={!!isDbRefreshing}
                                  >
                                    {isDbRefreshing === "full" ? (
                                      <Loader2Icon className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <RefreshCwIcon className="h-4 w-4" />
                                    )}
                                    <span className="inline-block min-w-[150px] text-center">
                                      Full Refresh
                                    </span>
                                  </Button>
                                </div>
                                <DialogFooter>
                                  <Button
                                    variant="outline"
                                    onClick={() =>
                                      setIsDbRefreshDialogOpen(false)
                                    }
                                    disabled={!!isDbRefreshing}
                                  >
                                    Cancel
                                  </Button>
                                </DialogFooter>
                              </DialogContent>
                            </Dialog>
                          ) : (
                            /* If incremental is NOT possible, just show a direct full refresh button */
                            <Button
                              variant="outline"
                              size="icon"
                              className="h-8 w-8 sm:h-9 sm:w-9 hover:bg-secondary/80"
                              title="Refresh Dataset (Full)"
                              onClick={() => handleDbRefresh("full")}
                              disabled={!!isDbRefreshing}
                            >
                              {isDbRefreshing === "full" ? (
                                <Loader2Icon className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                              ) : (
                                <RefreshCwIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                              )}
                            </Button>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}