import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DownloadIcon,
  PencilIcon,
  CheckIcon,
  XIcon,
  FileIcon,
  MessageSquareIcon,
  DatabaseIcon,
  TableIcon,
  RowsIcon,
  ClockIcon,
  HardDriveIcon,
  ChevronRightIcon,
  FolderIcon,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { updateDataset } from "@/lib/mutations/dataset/update-dataset";
import { Dataset } from "@/lib/api-client";
import Link from "next/link";
import { format } from "date-fns";

interface DatasetHeaderProps {
  dataset: Dataset;
  projectId: string;
  onUpdate?: () => Promise<void>;
}

export function DatasetHeader({
  dataset,
  projectId,
  onUpdate,
}: DatasetHeaderProps) {
  const { toast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [editedAlias, setEditedAlias] = useState(dataset.alias || "");
  const [editedDescription, setEditedDescription] = useState(
    dataset.description || "",
  );

  const handleUpdate = async () => {
    if (!onUpdate) return;
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
      await onUpdate();
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

  return (
    <div className="relative">
      {/* Main Grid Layout */}
      <div className="grid grid-cols-[400px,1fr] gap-8">
        {/* Left Column - Header Section */}
        <div className="space-y-3">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link
              href={`/${projectId}`}
              className="hover:text-primary transition-colors flex items-center gap-1"
            >
              <FolderIcon className="h-4 w-4" />
              Datasets
            </Link>
            <ChevronRightIcon className="h-4 w-4" />
            <span className="text-muted-foreground truncate">
              {dataset.name}
            </span>
          </div>

          <div className="flex items-start gap-3">
            <div className="bg-background/50 rounded-lg border p-2">
              <FileIcon className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              {isEditing ? (
                <div className="space-y-2">
                  <Input
                    value={editedAlias}
                    onChange={(e) => setEditedAlias(e.target.value)}
                    className="text-lg font-semibold h-9"
                    placeholder="Enter a friendly name..."
                  />
                  <div className="flex gap-2">
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleUpdate}
                      disabled={isUpdating}
                      className="h-7"
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCancel}
                      disabled={isUpdating}
                      className="h-7"
                    >
                      <XIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 mb-1">
                    <h1 className="text-lg font-semibold truncate">
                      {dataset.alias || "Untitled Dataset"}
                    </h1>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 rounded-full hover:bg-secondary/80"
                      onClick={() => setIsEditing(true)}
                    >
                      <PencilIcon className="h-3.5 w-3.5" />
                    </Button>
                    <Badge
                      variant="secondary"
                      className="h-5 px-1.5 text-xs font-medium bg-secondary/50"
                    >
                      CSV
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-1">
                    {dataset.description || "No description provided"}
                  </p>
                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 mt-6">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-9 w-9 hover:bg-secondary/80"
                      title="Download Dataset"
                    >
                      <DownloadIcon className="h-5 w-5" />
                    </Button>
                    <Link href={`/${projectId}/${dataset.id}/chat/`}>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-9 w-9 hover:bg-secondary/80"
                        title="Chat with Dataset"
                      >
                        <MessageSquareIcon className="h-5 w-5" />
                      </Button>
                    </Link>
                    <Link href={`/${projectId}/${dataset.id}/data/`}>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-9 w-9 hover:bg-secondary/80"
                        title="Query Dataset"
                      >
                        <DatabaseIcon className="h-5 w-5" />
                      </Button>
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Info Section */}
        <div className="pt-3 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            {/* Dataset Info - First Row */}
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <TableIcon className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Rows
                </div>
                <div className="text-sm font-semibold tabular-nums">
                  {new Intl.NumberFormat("en", {
                    notation: "compact",
                  }).format(dataset.row_count || 0)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <RowsIcon className="h-4 w-4 text-muted-foreground rotate-90" />
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Columns
                </div>
                <div className="text-sm font-semibold tabular-nums">
                  {dataset.columns.length}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <HardDriveIcon className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Size
                </div>
                <div className="text-sm font-semibold tabular-nums">
                  {dataset.size
                    ? `${(dataset.size / (1024 * 1024)).toFixed(1)} MB`
                    : "N/A"}
                </div>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {/* Dataset Info - Second Row */}
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <ClockIcon className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Created
                </div>
                <div className="text-[11px] font-medium">
                  {format(new Date(dataset.created_at), "MMM d, yyyy")}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <ClockIcon className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Updated
                </div>
                <div className="text-[11px] font-medium">
                  {format(new Date(dataset.updated_at), "MMM d, yyyy")}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Created by
                </div>
                <div className="text-[11px] font-medium">
                  {dataset.created_by}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-secondary/20 rounded-lg px-2.5 py-1.5">
              <div>
                <div className="text-[11px] font-medium text-muted-foreground">
                  Updated by
                </div>
                <div className="text-[11px] font-medium">
                  {dataset.updated_by}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
