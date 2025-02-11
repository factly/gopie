import { useState } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DownloadIcon, PencilIcon, CheckIcon, XIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { updateS3Dataset } from "@/lib/mutations/dataset/update-s3-dataset";
import { Dataset } from "@/lib/api-client";

interface DatasetHeaderProps {
  dataset: Dataset;
  onUpdate?: () => Promise<void>;
}

export function DatasetHeader({ dataset, onUpdate }: DatasetHeaderProps) {
  const { toast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [editedName, setEditedName] = useState(dataset.name);
  const [editedDescription, setEditedDescription] = useState(
    dataset.description || ""
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
      await updateS3Dataset({
        dataset: dataset.name,
        description: editedDescription,
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
    setEditedName(dataset.name);
    setEditedDescription(dataset.description || "");
    setIsEditing(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            {isEditing ? (
              <div className="flex items-center gap-2">
                <Input
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="text-2xl font-bold h-12 w-[300px]"
                  disabled
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleUpdate}
                  disabled={isUpdating}
                >
                  <CheckIcon className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCancel}
                  disabled={isUpdating}
                >
                  <XIcon className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <motion.div className="flex items-center gap-2">
                <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                  {dataset.name}
                </h1>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setIsEditing(true)}
                >
                  <PencilIcon className="h-4 w-4" />
                </Button>
              </motion.div>
            )}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", delay: 0.3 }}
            >
              <Badge variant="secondary" className="h-6 font-medium">
                CSV
              </Badge>
            </motion.div>
          </div>
          {isEditing ? (
            <div className="space-y-1">
              <Textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                placeholder="Add a description (min. 10 characters)..."
                className="h-20 resize-none"
              />
              <p className="text-xs text-muted-foreground">
                {editedDescription.length}/500 characters
              </p>
            </div>
          ) : dataset.description ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-muted-foreground max-w-[600px] flex items-center gap-2"
            >
              {dataset.description}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setIsEditing(true)}
              >
                <PencilIcon className="h-3 w-3" />
              </Button>
            </motion.p>
          ) : (
            <Button
              variant="ghost"
              className="text-muted-foreground"
              onClick={() => setIsEditing(true)}
            >
              <PencilIcon className="h-3 w-3 mr-2" />
              Add description
            </Button>
          )}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex items-center gap-4 text-muted-foreground pt-2"
          >
            <div className="flex items-center gap-1.5">
              <span className="font-medium">Rows:</span>
              <span>
                {new Intl.NumberFormat().format(dataset.row_count ?? 0)}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-medium">Columns:</span>
              <span>{dataset.columns.length}</span>
            </div>
          </motion.div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-9 hover:shadow-md transition-shadow"
        >
          <DownloadIcon className="mr-2 h-4 w-4" />
          Download Dataset
        </Button>
      </div>
    </div>
  );
}
