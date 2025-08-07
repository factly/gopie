import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  MoreHorizontal,
  Trash,
  PencilIcon,
  Calendar,
  Layers,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";
import { Project } from "@/lib/api-client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { useRouter } from "next/navigation";

interface ProjectCardProps {
  project: Project;
  onUpdate?: (
    projectId: string,
    data: { updated_by: string; name: string; description: string }
  ) => Promise<void>;
  onDelete?: (projectId: string) => Promise<void>;
}

export function ProjectCard({ project, onUpdate, onDelete }: ProjectCardProps) {
  const { toast } = useToast();
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [editedName, setEditedName] = useState(project.name);
  const [editedDescription, setEditedDescription] = useState(
    project.description
  );
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleDelete = async () => {
    if (!onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(project.id);
      toast({
        title: "Project deleted",
        description: "The project has been deleted successfully.",
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to delete project";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
    }
  };

  const handleUpdate = async () => {
    if (!onUpdate) return;
    if (editedName.length < 3) {
      toast({
        title: "Validation Error",
        description: "Project name must be at least 3 characters long.",
        variant: "destructive",
      });
      return;
    }
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
      await onUpdate(project.id, {
        name: editedName,
        description: editedDescription,
        updated_by: "admin",
      });
      setIsEditing(false);
      toast({
        title: "Project updated",
        description: "The project has been updated successfully.",
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to update project";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleChatClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Create context data for this dataset
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

  // Function to create a simple initial avatar from project name
  // const getInitialAvatar = (name: string) => {
  //   return name.charAt(0).toUpperCase();
  // };

  return (
    <>
      <Link href={`/projects/${project.id}`} className="block" prefetch={false}>
        <Card
          className={cn(
            "group transition-all duration-300 relative overflow-hidden border border-border/40 hover:border-border/80",
            "backdrop-blur-sm bg-card/80 hover:bg-card/90",
            "hover:shadow-lg hover:shadow-primary/5",
            "cursor-pointer"
          )}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <div
            className={cn(
              "absolute top-0 right-0 w-[50px] h-[50px] bg-gradient-to-br from-primary/10 to-primary/5",
              "transition-all duration-300 ease-in-out",
              isHovered ? "opacity-100" : "opacity-50"
            )}
          />

          <CardHeader className="pb-2">
            {/* Title section with right padding for chat icon */}
            <div className="flex items-start justify-between pr-[60px] mb-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                {/* <div className="flex-shrink-0 w-10 h-10  bg-primary/10 text-primary flex items-center justify-center font-medium select-none">
                  {getInitialAvatar(project.name)}
                </div> */}
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-xl font-semibold line-clamp-1 group-hover:text-primary transition-colors break-words">
                    {project.name}
                  </CardTitle>
                </div>
              </div>
            </div>
            
            {/* Description section using full width */}
            {project.description && (
              <p className="text-sm text-muted-foreground line-clamp-2 break-words">
                {project.description}
              </p>
            )}
            
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-0 right-0 h-[50px] w-[50px] p-0 z-10"
              onClick={handleChatClick}
            >
              <MessageSquare className="h-4 w-4" />
            </Button>
          </CardHeader>

          <CardContent>
            <div className="mt-2 pt-3 border-t border-border/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Layers className="h-3.5 w-3.5" />
                    <span className="font-medium">{project.datasetCount}</span>
                    <span>
                      {project.datasetCount === 1 ? "Dataset" : "Datasets"}
                    </span>
                  </div>

                  {project.createdAt && (
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>
                        {format(new Date(project.createdAt), "MMM d, yyyy")}
                      </span>
                    </div>
                  )}
                </div>

                <div
                  className={cn(
                    "flex items-center gap-1 text-xs font-medium text-primary opacity-0 transform translate-x-2",
                    "transition-all duration-300 ease-in-out",
                    isHovered ? "opacity-100 translate-x-0" : ""
                  )}
                >
                  <DropdownMenu modal={false}>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 "
                        onClick={(e: React.MouseEvent) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.preventDefault();
                          setIsEditing(true);
                        }}
                      >
                        <PencilIcon className="h-4 w-4 mr-2" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={(e) => {
                          e.preventDefault();
                          setIsDeleteDialogOpen(true);
                        }}
                      >
                        <Trash className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                  {/* <span>View Project</span>
                  <ChevronRight className="h-3 w-3" /> */}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </Link>

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the project &quot;{project.name}
              &quot; and all its datasets. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive hover:bg-destructive/90"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={isEditing} onOpenChange={setIsEditing} modal={false}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Project</DialogTitle>
            <DialogDescription>
              Make changes to your project here. Click save when you&apos;re
              done.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Input
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                placeholder="Project name"
              />
              <p className="text-xs text-muted-foreground">
                {editedName.length}/50 characters
              </p>
            </div>
            <div className="space-y-2">
              <Textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                placeholder="Project description"
              />
              <p className="text-xs text-muted-foreground">
                {editedDescription.length}/500 characters
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={isUpdating}>
              {isUpdating ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
