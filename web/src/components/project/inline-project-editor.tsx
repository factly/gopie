"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PencilIcon, CheckIcon, XIcon } from "lucide-react";
import { toast } from "sonner";
import { updateProject } from "@/lib/mutations/project/update-project";
import { useQueryClient } from "@tanstack/react-query";
import { Project } from "@/lib/api-client";

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
      <div className="space-y-4 animate-in fade-in">
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter project name"
              className="text-4xl font-semibold h-auto py-2 px-3"
              autoFocus
            />
          </div>
          <div className="flex items-center gap-2 pt-2">
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
          className="text-lg text-muted-foreground/90 resize-none min-h-[80px]"
          rows={3}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-4xl font-semibold tracking-tight text-foreground/90">
          {project.name}
        </h1>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-full"
          title="Edit Project"
          onClick={() => setIsEditing(true)}
        >
          <PencilIcon className="size-4" />
        </Button>
      </div>
      {project.description && (
        <p className="text-lg text-muted-foreground/90 max-w-[800px]">
          {project.description}
        </p>
      )}
    </div>
  );
}
