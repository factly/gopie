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
  MessageSquare,
} from "lucide-react";
import { toast } from "sonner";
import { updateProject } from "@/lib/mutations/project/update-project";
import { useQueryClient } from "@tanstack/react-query";
import { Project } from "@/lib/api-client";
import { format } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useRouter } from "next/navigation";

interface InlineProjectEditorProps {
  project: Project;
}

export function InlineProjectEditor({ project }: InlineProjectEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description || "");
  const [customPrompt, setCustomPrompt] = useState(project.custom_prompt || "");
  const queryClient = useQueryClient();
  const router = useRouter();

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }
    
    if (name.trim().length < 3 || name.trim().length > 50) {
      toast.error("Project name must be between 3 and 50 characters");
      return;
    }
    
    if (description.trim().length < 10) {
      toast.error("Project description must be at least 10 characters");
      return;
    }

    setIsUpdating(true);
    try {
      await updateProject(project.id, {
        name,
        description,
        custom_prompt: customPrompt,
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
    setCustomPrompt(project.custom_prompt || "");
    setIsEditing(false);
  };

  const handleChatWithProject = () => {
    // Create context data for this project
    const contextData = encodeURIComponent(
      JSON.stringify([
        {
          id: project.id,
          type: "project",
          name: project.name,
        },
      ])
    );

    router.push(`/chat?contextData=${contextData}`);
  };

  if (isEditing) {
    return (
      <Card className="border shadow-sm">
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
            <div className="space-y-1">
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, 1000))}
                placeholder="Enter project description"
                className="text-base text-muted-foreground/90 resize-none min-h-[80px]"
                rows={3}
                maxLength={1000}
              />
              <p className="text-xs text-muted-foreground">
                {description.length}/1000 characters
              </p>
            </div>
            <Textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Enter a custom prompt to guide AI interactions with this project's datasets..."
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
    <Card className="border shadow-sm relative">
      <div className="absolute top-0 right-0 w-[50px] h-[50px] bg-gradient-to-br from-primary/10 to-primary/5 transition-all duration-300 ease-in-out opacity-100" />
      
      <CardContent className="p-6">
        <div className="space-y-3 pr-[60px]">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {project.name}
            </h1>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 hover:bg-muted"
              title="Edit Project"
              onClick={() => setIsEditing(true)}
            >
              <PencilIcon className="size-4" />
            </Button>
          </div>

          <div className="min-h-[40px]">
            {project.description ? (
              <p className="text-base text-muted-foreground/90 line-clamp-2">
                {project.description}
              </p>
            ) : (
              <p className="text-base text-muted-foreground/90 opacity-0">
                &nbsp;
              </p>
            )}
          </div>

          {project.custom_prompt && (
            <div className="mt-3">
              <p className="text-sm font-medium text-muted-foreground mb-1">Custom Prompt:</p>
              <p className="text-sm text-muted-foreground/90 line-clamp-2">
                {project.custom_prompt}
              </p>
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="absolute top-0 right-0 h-[50px] w-[50px] p-0 z-10"
          title="Chat with Project"
          onClick={handleChatWithProject}
        >
          <MessageSquare className="h-4 w-4" />
        </Button>

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
