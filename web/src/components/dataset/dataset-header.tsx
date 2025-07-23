import { useState } from "react";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

interface DatasetHeaderProps {
  dataset: Dataset;
  projectId: string;
  onUpdate?: () => Promise<void>;
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
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [editedAlias, setEditedAlias] = useState(dataset.alias || "");
  const [editedDescription, setEditedDescription] = useState(
    dataset.description || ""
  );

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
        <div className="flex items-start gap-4 flex-1 min-w-0 pr-[60px]">
          <div className="flex-1 min-w-0 space-y-3">
            {/* Title and Badge */}
            {isEditing ? (
              <div className="space-y-3">
                <Input
                  value={editedAlias}
                  onChange={(e) => setEditedAlias(e.target.value)}
                  className="text-2xl font-bold h-11 text-foreground"
                  placeholder="Enter a friendly name..."
                />
                <div className="space-y-2">
                  <Textarea
                    value={editedDescription}
                    onChange={(e) => setEditedDescription(e.target.value)}
                    className="resize-none min-h-[100px]"
                    placeholder="Enter a description..."
                    rows={4}
                  />
                  <div className="flex gap-2">
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
                      variant="ghost"
                      size="sm"
                      onClick={handleCancel}
                      disabled={isUpdating}
                    >
                      <XIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                  </div>
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
                    <p className="text-muted-foreground leading-relaxed flex-1 min-h-[60px] pr-8">
                      {dataset.description || "No description provided"}
                    </p>
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

                {/* Quick Stats */}
                <div className="flex items-center justify-between gap-4 text-sm">
                  <div className="flex items-center gap-4">
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
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-muted-foreground hover:text-foreground"
                        >
                          <InfoIcon className="h-4 w-4 mr-1" />
                          More details
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
                          <h4 className="font-medium text-sm">Contributors</h4>
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
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-9 w-9 hover:bg-secondary/80"
                        title="Download Dataset"
                      >
                        <DownloadIcon className="h-5 w-5" />
                      </Button>
                      <Link href={`/projects/${projectId}/datasets/${dataset.id}/data/`}>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-9 w-9 hover:bg-secondary/80"
                          title="Query Dataset"
                        >
                          <DatabaseIcon className="h-5 w-5" />
                        </Button>
                      </Link>
                      <Link href={`/projects/${projectId}/datasets/${dataset.id}/api`}>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-9 w-9 hover:bg-secondary/80"
                          title="API Playground"
                        >
                          <CodeIcon className="h-5 w-5" />
                        </Button>
                      </Link>
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
