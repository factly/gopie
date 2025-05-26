"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  PencilIcon,
  CheckIcon,
  XIcon,
  CalendarIcon,
  UserIcon,
} from "lucide-react";
import { toast } from "sonner";
import { updateProject } from "@/lib/mutations/project/update-project";
import { useQueryClient } from "@tanstack/react-query";
import { Project } from "@/lib/api-client";
import { format } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface InlineProjectEditorProps {
  project: Project;
}

export function InlineProjectEditor({ project }: InlineProjectEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description || "");
  const queryClient = useQueryClient();

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }

    setIsUpdating(true);
    try {
      await updateProject(project.id, {
        name,
        description,
        updated_by: "gopie-web-ui",
      });

      // Invalidate both project and datasets queries
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["project", { projectId: project.id }],
        }),
        queryClient.invalidateQueries({
          queryKey: ["datasets", { projectId: project.id }],
        }),
        queryClient.invalidateQueries({
          queryKey: ["projects"],
        }),
      ]);

      toast.success("Project updated successfully");
      setIsEditing(false);
    } catch (error) {
      console.error(error);
      toast.error("Failed to update project. Please try again.");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCancel = () => {
    setName(project.name);
    setDescription(project.description || "");
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <Card className="bg-gradient-to-b from-background to-muted/30 border shadow-sm">
        <CardContent className="p-6">
          <div className="space-y-4 animate-in fade-in">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter project name"
                  className="text-2xl font-semibold h-auto py-2 px-3"
                  autoFocus
                />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
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
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter project description"
              className="text-base text-muted-foreground/90 resize-none min-h-[80px]"
              rows={3}
            />
          </div>
        </CardContent>
      </Card>
    );
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "MMM d, yyyy");
    } catch {
      return "Unknown date";
    }
  };

  return (
    <Card className="bg-gradient-to-b from-background to-muted/30 border shadow-sm">
      <CardContent className="p-6">
        <div className="flex justify-between items-start">
          <div className="space-y-3 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                {project.name}
              </h1>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-full hover:bg-muted"
                title="Edit Project"
                onClick={() => setIsEditing(true)}
              >
                <PencilIcon className="size-4" />
              </Button>
            </div>

            {project.description && (
              <p className="text-base text-muted-foreground/90 max-w-[800px]">
                {project.description}
              </p>
            )}
          </div>
        </div>

        <Separator className="my-4" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <CalendarIcon className="size-4" />
            <span>Created:</span>
            <span className="font-medium text-foreground">
              {formatDate(project.createdAt)}
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <CalendarIcon className="size-4" />
            <span>Updated:</span>
            <span className="font-medium text-foreground">
              {formatDate(project.updatedAt)}
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <UserIcon className="size-4" />
            <span>Created by:</span>
            <span className="font-medium text-foreground">
              {project.createdBy}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
